# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います: https://semver.org/

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

初回公開リリース。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 に設定。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env パーサ実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理等に対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / システム設定（env, log_level, is_live 等）をプロパティ経由で取得。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL）と必須値チェックを実装。

- Data 層 (src/kabusys/data/)
  - J-Quants クライアント (data/jquants_client.py)
    - レート制限（120 req/min）を守る固定間隔スロットリング実装。
    - 再試行ロジック（指数バックオフ、最大試行回数、408/429/5xx のリトライ挙動）を実装。
    - 401 に対する自動トークンリフレッシュ（1 回）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT によるアップサート）。
    - データ保存時に fetched_at を UTC で記録することで取得時点をトレース可能に。
    - 型変換ユーティリティ (_to_float / _to_int) を実装。
  - ニュース収集モジュール (data/news_collector.py)
    - RSS フィードから記事を収集する基盤を実装（デフォルトソースに Yahoo Finance）。
    - 安全な XML パース（defusedxml）や受信サイズ上限（10MB）、URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）などを考慮。
    - 記事ID 生成、トラッキングパラメータ除去、DB への冪等保存（ON CONFLICT / INSERT チャンク処理）を想定した設計を実装（多くのユーティリティが含まれる）。
    - SSRF・XML Bomb 等を考慮した防御方針を実装方針として導入。

- 研究・ファクター計算 (src/kabusys/research/)
  - ファクター計算モジュール (research/factor_research.py)
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離率）を実装。
    - ボラティリティ calc_volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）を実装。
    - バリュー calc_value（最新の raw_financials と株価を使った PER / ROE）を実装。
    - DuckDB を用いた効率的なウィンドウ集計（必要なスキャン範囲のバッファ調整）を採用。
  - 特徴量探索 (research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン、1/5/21 日がデフォルト）。
    - IC 計算 calc_ic（Spearman の ρ をランクで計算、最小サンプル数チェック）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
    - ランク変換ユーティリティ rank（同順位は平均ランク扱い、丸め処理で ties を安定化）。
  - research パッケージの公開 API を整理（__init__.py）。

- 戦略層 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (strategy/feature_engineering.py)
    - 研究環境で計算した raw factor を集約・正規化して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を導入。
    - Z スコア正規化→±3 クリップ→features への日付単位の置換（トランザクションによる原子性）を実装。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを利用する設計。
  - シグナル生成 (strategy/signal_generator.py)
    - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
    - デフォルト重み・閾値（weights と threshold）、ユーザー指定 weights の検証・正規化・再スケール処理を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算（シグモイド変換、欠損は中立 0.5 で補完）。
    - Bear レジーム検知（AI レジームスコアの平均が負の場合、サンプル数閾値あり）により BUY を抑制。
    - エグジット判定（stop_loss: -8% 以下、score_drop: final_score < threshold）による SELL シグナル生成。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）と signals テーブルへの日付単位の置換（トランザクション）。
  - strategy パッケージの公開 API（build_features, generate_signals）を整理。

- その他
  - research/__init__.py と strategy/__init__.py で主要関数を公開。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML ベースの攻撃（XML Bomb 等）に対処。
- ニュース URL の正規化とトラッキングパラメータ除去、HTTP/HTTPS スキームチェック等を想定し、SSRF やトラッキング漏洩のリスク軽減を設計に反映。
- J-Quants クライアントはトークン管理と自動リフレッシュを実装し、認証失敗時の安全な挙動を確保。

### 既知の制限 / 未実装の項目
- signal_generator のトレーリングストップ・時間決済（保有 60 営業日超過）など一部エグジット条件は未実装（positions テーブルに追加情報が必要）。
- news_collector は収集〜紐付け〜ID生成までの基盤を備えるが、完全なパイプライン（シンボル紐付けロジック等）は今後追加予定。
- 一部モジュールは kabusys.data.stats など他モジュールとの連携を前提（別ファイルに実装されている想定）。

---

依存・実行要件（概略）
- DuckDB（データ格納・クエリ実行）
- defusedxml（ニュース XML の安全なパース）
- 標準ライブラリ（urllib, datetime, logging 等）

詳細な使用例・設計仕様（StrategyModel.md, DataPlatform.md 等）はリポジトリ内のドキュメントを参照してください。