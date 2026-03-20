# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

（現在の作業ブランチ用のエントリがあればここに記載してください）

---

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加点・設計方針です。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョン `__version__ = "0.1.0"` を定義。公開モジュールとして data / strategy / execution / monitoring をエクスポート。

- 環境設定モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
  - プロジェクトルート検出: __file__ を起点に親ディレクトリを探索し `.git` または `pyproject.toml` を基準にプロジェクトルートを特定。
  - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
  - .env の読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - .env パーサ:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート対応（バックスラッシュエスケープ処理付き）。
    - インラインコメントの取り扱い（クォート有無で振る舞いを区別）。
  - Settings クラス:
    - 必須の環境変数取得メソッド `_require`（未設定時は ValueError を送出）。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供。
    - `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の検証。
    - is_live / is_paper / is_dev ヘルパー。

- Data (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限: 固定間隔スロットリングで 120 req/min を維持する RateLimiter を実装。
    - リトライ: 指数バックオフ（最大 3 回）。HTTP 408/429 と 5xx をリトライ対象に含む。
    - 401 Unauthorized を検知した場合はリフレッシュトークンから ID トークンを自動更新して 1 回リトライ。
    - ID トークンはモジュールレベルでキャッシュしページネーション間で共有。
    - ページネーション対応の fetch 関数: daily_quotes / financial_statements / market_calendar。
    - DuckDB への保存関数 (save_daily_quotes / save_financial_statements / save_market_calendar) を実装し、ON CONFLICT DO UPDATE による冪等保存を行う。
    - 保存処理は PK 欠損行のスキップとログ出力を行う。
    - HTTP 実装は urllib を使用し、JSON デコード失敗やネットワークエラーに対するハンドリングを行う。
    - ユーティリティ: 型安全な _to_float / _to_int 変換関数。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集機能を実装（デフォルトソースに Yahoo Finance のビジネス RSS を含む）。
  - セキュリティ設計:
    - defusedxml を使用して XML Bomb 等を防御。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を予防。
    - トラッキングパラメータ（utm_* 等）を除去する URL 正規化処理を実装。
    - URL 正規化時にスキーム・ホストの小文字化、フラグメント除去、クエリをキーでソート。
  - DB 保存はバルク INSERT（チャンクサイズ _INSERT_CHUNK_SIZE）で処理する設計。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）にすることで冪等性を想定（設計方針に記載）。

- 研究用モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR（20日）、出来高関連、20日平均売買代金、PER/ROE（raw_financials ベース）等のファクター計算を実装。
    - DuckDB のウィンドウ関数を用いて効率的に計算。
    - データ不足時の None 返却や、スキャン範囲のバッファ設計を実施。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）を実装。horizons デフォルト [1,5,21]。
    - IC（Spearman の ρ）計算（calc_ic）とランク関数（rank）を実装。ties は平均ランクで処理、丸めによる ties 検出対策を実施。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
  - 研究ユーティリティ群を re-export。

- 戦略モジュール (kabusys.strategy)
  - feature_engineering.build_features:
    - research の calc_* 結果を取りまとめ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化（zscore_normalize を利用）、±3 でクリップし、features テーブルへ日付単位で置換（DELETE + INSERT）し原子性を保証。
    - ユニットは DuckDB 接続を受け取り外部 API には依存しない設計。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントはシグモイド変換や PER に基づく値変換などを行う。
    - デフォルトの重みを提供し、ユーザ定義 weights を検証・補完・正規化（合計 1 に再スケール）するロジック。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）で BUY シグナルを抑制。
    - BUY 条件: final_score >= threshold（デフォルト 0.60）。SELL 条件: ストップロス（終値基準で -8%）またはスコア低下。
    - 保有ポジション（positions）に対するエグジット判定と SELL シグナル生成を実装。SELL 優先ポリシーにより該当銘柄は BUY から除外。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）で冪等性を確保。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- XML 処理に defusedxml を採用（news_collector）。
- RSS レスポンスサイズ制限や URL 正規化、SSRF を意識した設計注記あり。
- J-Quants クライアントでのトークン自動リフレッシュは 1 回のみのリトライに限定して無限再帰を防止。

---

注記:
- 上記はリポジトリ内の実装・ドキュメント文字列から推測してまとめた CHANGELOG です。実際のコミット履歴や外部ドキュメント（Design/StrategyModel.md 等）が存在する場合、それらに基づきさらに詳細化・修正してください。