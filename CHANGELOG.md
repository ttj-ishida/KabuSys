Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての変更はセマンティックバージョニングに従います。  
このファイルはパッケージバージョン __version__ = "0.1.0" に対応する初期リリースの内容を、コード内のドキュメンテーションから推測してまとめたものです。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-19
-------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義

- 環境設定/読み込み機能（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
  - .env パーサーは export 形式・クォート・インラインコメント・エスケープに対応
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /実行環境（development/paper_trading/live）/ログレベルなどのプロパティを型付きで取得・検証
  - 必須項目取得時に未設定なら ValueError を送出する _require を追加

- データ取得・保存（src/kabusys/data/）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API レート制限（120 req/min）を守る固定間隔スロットリングの RateLimiter 実装
    - リトライ（指数バックオフ）と 401 時の自動トークンリフレッシュ処理を実装
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装
    - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT による更新）
    - 取得タイムスタンプは UTC で記録（look-ahead bias 対策）
    - 型変換ユーティリティ _to_float / _to_int を実装（堅牢な変換ルール）
  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィード収集機能を実装（デフォルトソースに Yahoo Finance）
    - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント除去）と記事 ID 生成（正規化後の URL の SHA-256 の先頭 32 文字）
    - defusedxml を用いた安全な XML パース、受信サイズ上限（10MB）、HTTP スキーム検証などセキュリティ対策を実装
    - raw_news への冪等保存（ON CONFLICT / DO NOTHING 想定）・銘柄紐付け設計（news_symbols）
    - バルク挿入のチャンク化で SQL 長やパラメータ数を制御

- 研究（research）モジュール（src/kabusys/research/）
  - factor_research.py: prices_daily/raw_financials を使ったファクター計算を実装
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）
    - calc_volatility: 20 日 ATR（atr_20/atr_pct）、20 日平均売買代金、volume_ratio
    - calc_value: latest raw_financials と株価を組み合わせて PER / ROE を算出
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得
    - calc_ic: ファクターと将来リターンのスピアマン IC（ランク相関）を計算
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクで扱うランク関数（丸め処理で ties 判定を安定化）
  - research パッケージ __init__ で主要 API を再エクスポート

- 戦略（strategy）モジュール（src/kabusys/strategy/）
  - feature_engineering.build_features:
    - research 側で計算された生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ
    - 日付単位で features テーブルへトランザクショナルに置換（DELETE→INSERT をトランザクションで実行、冪等）
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算
    - コンポーネントはシグモイド変換・逆転等のロジックを経て最終スコア final_score を算出（デフォルト閾値 BUY=0.60）
    - AI の regime_score 集計により Bear レジームを判定（サンプル閾値あり）し、Bear 時は BUY を抑制
    - 保有ポジションに対するエグジット条件（ストップロス -8%、スコア低下）を実装（_generate_sell_signals）
    - SELL を優先して BUY リストから除外、signals テーブルへ日付単位の置換で保存（トランザクション）
    - ユーザ定義 weights の検証と正規化（未知キーや負値・非数は無視、合計 1 にスケール）
  - strategy パッケージ __init__ で主要 API を再エクスポート

- パッケージ全体の設計注記（ドキュメント文字列）
  - ルックアヘッドバイアス回避のため「target_date 時点のデータのみを使用」方針が明記
  - 発注層（execution）への直接依存を持たない設計
  - DuckDB を中心としたデータパイプラインと冪等性確保（ON CONFLICT / トランザクション）

Security
- news_collector で defusedxml を使用、受信サイズ上限、HTTP スキーム検証等により XML Bomb / SSRF / メモリ DoS の軽減策を実装
- jquants_client のトークン・HTTP エラー処理で不正なレスポンスに対する堅牢化（JSON デコード失敗時は明示的エラー）

Known limitations / Todo
- signal_generator の一部エグジット条件は未実装（doc の TODO 注記）
  - トレーリングストップ（peak_price 必要）
  - 時間決済（entry_date に基づく経過日数判定）
- execution モジュールは現段階で実装ファイルが空（発注層実装は別途）
- 一部テーブルスキーマ（positions の peak_price / entry_date など）や外部システム（Slack/posting 等）は実運用向けに追加実装が必要
- news_collector の保存テーブル名や raw_news の具体スキーマはコード中では仮定（実環境の DB スキーマに合わせて調整が必要）

Notes
- 本 CHANGELOG はコード内の docstring / 関数名・実装から推測して作成しています。実際のリリースノートには別途変更差分やマイグレーション手順を追加してください。