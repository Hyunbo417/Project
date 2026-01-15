import pandas as pd
import plotly.express as px
import streamlit as st

df = pd.read_csv("premierleague.csv")
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
df = df.sort_values('Date').reset_index(drop=True)

# Round Define
df['Round'] = (df.index // 10) + 1
    
# Probability Define
df['B365H_P'] = 1 / df['B365H']
df['B365D_P'] = 1 / df['B365D']
df['B365A_P'] = 1 / df['B365A']
    
# Favorit Define
df['Favorite'] = df[['B365H_P', 'B365D_P', 'B365A_P']].idxmax(axis=1).str[4]
df['Favorite_Won'] = df['Favorite'] == df['FTR']

df['Total_Cards'] = df['HY'] + df['AY'] + df['HR'] + df['AR']
df['Total_Fouls'] = df['HF'] + df['AF']

st.sidebar.header("🎮 Dashboard Control")
selected_team = st.sidebar.selectbox("Select Team", ["Whole Team"] + sorted(df['HomeTeam'].unique().tolist()))
round_range = st.sidebar.slider("Round Range Select", 1, 38, (1, 38))

# Data Filtering
mask = (df['Round'] >= round_range[0]) & (df['Round'] <= round_range[1])
if selected_team != "Whole Team":
    mask &= (df['HomeTeam'] == selected_team) | (df['AwayTeam'] == selected_team)
filtered_df = df[mask].copy()


st.title("⚽ PL 24/25 Analysis")
st.markdown(f"**Selected Team:** {selected_team} | **Round:** {round_range[0]} ~ {round_range[1]}")

col1, col2, col3, col4 = st.columns(4)
correct_rate = filtered_df['Favorite_Won'].mean() * 100
total_matches = len(filtered_df)

# Profit by Team
def get_team_profit(data):
    teams = sorted(data['HomeTeam'].unique())
    profits = []
    for t in teams:
        t_matches = data[(data['HomeTeam'] == t) | (data['AwayTeam'] == t)]
        p = t_matches.apply(lambda r: (r['B365H']-1 if r['FTR']=='H' else -1) if r['HomeTeam']==t 
                            else (r['B365A']-1 if r['FTR']=='A' else -1), axis=1).sum()
        profits.append({'Team': t, 'Profit': p})
    return pd.DataFrame(profits).sort_values('Profit', ascending=False)

team_profit_df = get_team_profit(df)

col1.metric("Total Matches", f"{total_matches}")
col2.metric("Correct Rate", f"{correct_rate:.1f}%")
col3.metric("Most Upset Team", team_profit_df.iloc[0]['Team'])
col4.metric("Most Profit", f"+{team_profit_df.iloc[0]['Profit']:.2f}")

# Visualization
tab1, tab2, tab3 = st.tabs(["📈 Profit Analysis", "📊 Statics", "👨‍⚖️ Refree"])

with tab1:
    # Total Profit calculate
    def calc_strategy_profit(row):
        fav = row['Favorite']
        return row[f'B365{fav}'] - 1 if row['FTR'] == fav else -1
    
    filtered_df['Profit'] = filtered_df.apply(calc_strategy_profit, axis=1)
    filtered_df['Cum_Profit'] = filtered_df['Profit'].cumsum()
    
    fig_line = px.line(filtered_df, x='Date', y='Cum_Profit', 
                       title="Changes in cumulative assets at full-time betting (based on 1 unit)",
                       template="plotly_dark", color_discrete_sequence=['#00ff88'])
    st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    # Correct bets by Round
    round_stats = filtered_df.groupby('Round')['Favorite_Won'].sum().reset_index()
    fig_bar = px.bar(round_stats, x='Round', y='Favorite_Won',
                     title="Number of hits per round (out of 10 games)",
                     color='Favorite_Won', color_continuous_scale='RdYlGn')
    st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    st.subheader("👨‍⚖️ Refree Analysis (Atleast 5 games)")
    
    # Statics by Refree
    ref_stats = df.groupby('Referee').agg({
        'Date': 'count',
        'Total_Cards': 'mean',
        'Total_Fouls': 'mean',
        'Is_Upset': 'mean'
    }).reset_index()
    
    ref_stats.columns = ['Name', 'Games', 'Mean_Cards', 'Mean_Fouls', 'Upset_prob']
    ref_stats['Upset_prob'] = (ref_stats['Upset_prob'] * 100).round(1)
    
    # 5 games
    ref_stats = ref_stats[ref_stats['Games'] >= 5].sort_values('Mean_Cards', ascending=False)

    # Visualisation of cards
    fig_ref_cards = px.bar(ref_stats, x='Name', y='Mean_Cards', 
                           color='Mean_Cards', title="Mean Cards by Refree",
                           color_continuous_scale='OrRd')
    st.plotly_chart(fig_ref_cards, use_container_width=True)

    # Visualisation of upset
    fig_ref_upset = px.scatter(ref_stats, x='Mean_Fouls', y='Upset_prob', 
                               size='Games', hover_name='Name', text='Name',
                               title="Relationship between Fouls and Upset Game",
                               labels={'Upset_prob': 'Upset Probability (%)', 'Mean_Fouls': 'Mean Fouls'})
    st.plotly_chart(fig_ref_upset, use_container_width=True)

    st.info("💡 팁: 산점도에서 우측 상단에 위치한 심판일수록 경기를 엄격하게 운영하며, 해당 심판의 경기에서 예상 밖의 결과가 자주 나왔음을 의미합니다.")


# Data Table
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("🚨 Upsets TOP 10")
    # Upset
    upsets = filtered_df[~filtered_df['Favorite_Won']].copy()
    upsets['Winner_Odds'] = upsets.apply(lambda r: r[f"B365{r['FTR']}"], axis=1)
    st.dataframe(upsets[['Date', 'HomeTeam', 'AwayTeam', 'FTR', 'Winner_Odds']]
                 .sort_values('Winner_Odds', ascending=False).head(10), use_container_width=True)

with c2:
    st.subheader("💰 Profit Table")
    st.dataframe(team_profit_df.style.background_gradient(subset=['Profit'], cmap='RdYlGn'), use_container_width=True)



    
