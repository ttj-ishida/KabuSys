# Changelog

すべての変更は「Keep a Changelog」準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## Unreleased
- なし

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要コンポーネントと機能を追加しています。

### Added
- パッケージ基礎
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に登録

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定読み込みを自動化（プロジェクトルートは .git or pyproject.toml で検出）
  - .env と .env.local の優先順位（OS 環境変数 > .env.local > .env）での読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション（テスト用途）
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント対応
  - Settings クラス: 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、デフォルト値（KABUSYS_ENV, LOG_LEVEL, データベースパス等）、入力検証（KABUSYS_ENV / LOG_LEVEL の許容値）、ユーティリティプロパティ（is_live/is_paper/is_dev）

- データ取得 / 保存（kabusys.data）
  - J-Quants クライアント (jquants_client.py)
    - API 呼び出しユーティリティ（_request）: レート制限（固定間隔スロットリング）、リトライ（指数バックオフ、最大 3 回）、特定ステータス(408/429/5xx)でのリトライ、429 の Retry-After 優先
    - 401 発生時の自動トークンリフレッシュをサポート（1 回のみリフレッシュして再試行）
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）: 冪等性を考慮した INSERT ... ON CONFLICT DO UPDATE を利用、PK 欠損行のスキップ通知、fetched_at に UTC タイムスタンプを付与
    - 型変換ユーティリティ (_to_float / _to_int) を実装して入力の堅牢性を確保
  - ニュース収集モジュール (news_collector.py)
    - RSS フィード収集と raw_news への冪等保存を実装（記事 ID は正規化 URL の SHA-256 ハッシュ先頭等を想定）
    - セキュリティ対策: defusedxml を使用した XML パース、受信サイズ制限 (MAX_RESPONSE_BYTES)、SSRF 回避（非 http/https を拒否 など）、トラッキングパラメータ除去、URL 正規化、バルク INSERT チャンク処理、INSERT RETURNING による挿入件数精査
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を登録

- 研究用モジュール（kabusys.research）
  - ファクター計算 (factor_research.py)
    - Momentum ファクター: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）
    - Volatility / Liquidity ファクター: ATR 20 日（atr_20, atr_pct）、20 日平均売買代金 (avg_turnover)、出来高比率 (volume_ratio)
    - Value ファクター: per / roe（raw_financials から最新財務を取得し価格と組み合わせて算出）
    - DuckDB の SQL とウィンドウ関数を活用した高効率計算（営業日欠損・データ不足時は None を返す設計）
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1/5/21 日をデフォルト）
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク計算で算出、サンプル不足時は None）
    - 統計サマリー factor_summary（count/mean/std/min/max/median）
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めによる ties 対応）

  - 研究 API を kabusys.research パッケージとしてエクスポート

- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング (feature_engineering.py)
    - research の生ファクターを結合してユニバースフィルタ（最低株価 / 最低平均売買代金）適用
    - 正規化: zscore_normalize を呼び出し、Z スコアを ±3 でクリップ
    - features テーブルへの日付単位の置換（トランザクション + バルク挿入で冪等性・原子性を担保）
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算
    - final_score は重み付き合算（デフォルト重みを実装）、weights の入力検証と正規化を実装
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、ただしサンプル閾値あり）
    - BUY: threshold 超過で買いシグナルを生成（Bear 時は BUY を抑制）
    - SELL: 保有ポジションに対するエグジット判定（ストップロス -8% / final_score が閾値未満）。SELL 優先で BUY から除外。
    - signals テーブルへの日付単位置換（冪等）
  - strategy パッケージの公開 API: build_features, generate_signals

- その他
  - DuckDB を前提とした SQL 設計と SQL + Python のハイブリッド実装により、外部ライブラリに依存しない設計を採用

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- ニュース収集: defusedxml の導入、受信サイズ制限、URL 正規化により XML Bomb / メモリ DoS / SSRF 対策を実装
- J-Quants クライアント: トークン管理とリトライポリシーにより認証例外やレート超過時の脆弱性を低減

### Notes / Known issues / TODOs
- signal_generator のエグジットロジックは以下を未実装（コード内に記載された将来の拡張案）
  - トレーリングストップ（positions テーブルに peak_price が必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の記事 ID 生成・news_symbols への紐付けなどの詳細実装は設計に基づくが、運用時のマッピングロジック調整が必要
- config._find_project_root は .git / pyproject.toml を基準にしているため、配布方法によっては自動 .env ロードをスキップする可能性あり（その場合は環境変数で設定を渡すこと）
- generate_signals の weights 引数は未知キー・NaN/Inf・負値をスキップする実装のため、外部から与える場合は正規化済みの辞書を渡すことを推奨
- 単体テスト・統合テストのカバレッジはリリース時点で限定的。特に外部 API 呼び出し周り（レート制御・リトライ挙動）はモックテストの整備が望まれる

---

（本 CHANGELOG はソースコード内の docstring と実装内容から推測して作成しています。実際の運用・次バージョンでは挙動・API 仕様が変更される可能性があります。）