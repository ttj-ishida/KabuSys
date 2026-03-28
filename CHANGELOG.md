# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
- （現時点でのリリースは 0.1.0 のみ。今後の変更はここに記載されます）

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。パブリック API として data, strategy, execution, monitoring をエクスポート。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定管理 (kabusys.config)
  - .env および環境変数から設定を自動ロードする機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - .env/.env.local の優先度管理（OS 環境変数保護、override 挙動、.env.local による上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート（テスト用途）。
  - .env 行パーサの実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル等の設定プロパティを公開。
  - 必須環境変数未設定時に明確なエラーメッセージを投げる _require() を実装。env 値の検証（KABUSYS_ENV, LOG_LEVEL）を導入。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン基盤（pipeline.ETLResult を含む）を実装。ETL 実行結果を表すデータクラスを提供。
  - calendar_management:
    - JPX マーケットカレンダー管理と夜間更新ジョブ (calendar_update_job) を実装。J-Quants クライアント経由で差分取得し冪等的に保存。
    - 営業日判定ユーティリティ群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB の有無や未登録日を考慮した曜日ベースのフォールバック、最大探索日数上限、安全性（バックフィル・健全性チェック）を導入。
  - ETL パイプライン（kabusys.data.pipeline）:
    - 差分フェッチ、保存（idempotent）、品質チェックのための結果構造とユーティリティ実装。
    - 最小データ日付、calendar lookahead、バックフィル日数等の定数を導入。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news / news_symbols を参照し、指定ウィンドウのニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）にバッチ送信しセンチメントを ai_scores テーブルへ保存する score_news を実装。
    - バッチサイズ、1銘柄あたりの記事・文字数上限、タイムウィンドウ計算（JST 基準の UTC 変換）を実装。
    - JSON Mode を利用した厳格なレスポンスバリデーション、スコアクリッピング (±1.0)、レスポンス復元ロジックを実装。
    - 429/ネットワーク断/タイムアウト/5xx を対象とした指数バックオフのリトライ処理を実装。失敗時は個別チャンクをスキップして他銘柄を保護。
    - DuckDB の executemany の空リスト制約（DuckDB 0.10）に対応した安全な書込みロジック（DELETE→INSERT）を実装。
  - レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily / raw_news を参照し、ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを行う。
    - OpenAI 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。API キー注入対応、内部の再試行・5xx 判定ロジックを実装。
    - OpenAI 呼出しは news_nlp とは独立した実装で、モジュール結合を避ける設計。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR20、相対 ATR、20日平均売買代金、出来高比等の計算を提供。データ不足時の None 扱い。
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）を実装。
    - calc_ic（スピアマンランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - kabusys.data.stats からの zscore_normalize を再エクスポート。

### 修正 (Fixed)
- DuckDB 互換性
  - executemany に空リストを渡せない環境（DuckDB 0.10）への対応を行い、空パラメータ時には実行をスキップすることでエラーを防止。
- JSON レスポンス処理の堅牢化
  - OpenAI の JSON mode でも前後の余計なテキストが混入するケースへ対応するため、最外郭の {} を抽出してパースする復元ロジックを追加。
- レート制限／ネットワーク障害に対するフェイルセーフ
  - news_nlp と regime_detector 両方でリトライとフォールバック（スコア 0.0 またはチャンクスキップ）の戦略を導入し、外部API障害時にもプロセス全体が停止しないようにした。

### 仕様・設計上の注意 (Notes)
- ルックアヘッドバイアス防止
  - score_news / score_regime を含む時系列処理関数は datetime.today()/date.today() を直接参照しない設計。必ず外部から target_date を渡すことで将来情報の混入を防止。
- OpenAI API
  - gpt-4o-mini を想定し JSON Mode を利用。テスト容易性のため _call_openai_api をモック可能にしている（unittest.mock.patch）。
  - API キーは関数引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
- DB 書き込みは冪等性を重視
  - market_regime / ai_scores / market_calendar 等の更新は DELETE→INSERT または ON CONFLICT ベースで冪等に実行するよう設計。
- ロギング
  - 各処理において警告・情報ログを適切に出力し、異常時のデバッグと運用監視を想定。

### 既知の制約・将来の改善候補
- 一部機能（例: strategy / execution / monitoring）の詳細実装はリリース時点で最小限または未実装の可能性がある（パッケージエクスポートは存在）。
- OpenAI レスポンス検証のルールやプロンプトは将来的なモデル挙動に応じて調整が必要。
- DuckDB バージョン違いに起因するクエリ/バインドの互換性については追加の統合テストが必要。

---

（注）上記は提供されたコードベースの実装内容から推測して作成した CHANGELOG です。実際のリリースノートはコミット履歴やプロジェクト運用方針に応じて調整してください。