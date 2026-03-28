# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測してまとめた主な追加・設計方針・動作上の注意点です。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージルート: kabusys（__version__ = 0.1.0）
  - エクスポート済みサブパッケージ: data, strategy, execution, monitoring

- 設定・環境変数管理（src/kabusys/config.py）
  - .env 自動読み込み機能（プロジェクトルートの .git または pyproject.toml を基準に探索）
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応
    - クォートなし値のインラインコメント処理（直前が空白/タブの '#' をコメント扱い）
  - protected 機能により OS 環境変数の上書きを保護可能
  - Settings クラスにより各種必須設定をプロパティで取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH
  - KABUSYS_ENV（development / paper_trading / live）のバリデーションおよび LOG_LEVEL 検証

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント解析: score_news（src/kabusys/ai/news_nlp.py）
    - OpenAI（gpt-4o-mini）を使った銘柄別センチメント算出
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）
    - 銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）
    - バッチ処理: 1 API 呼び出しあたり最大 20 銘柄
    - JSON Mode を期待し、レスポンスの厳密なバリデーションを実装
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ
    - フェイルセーフ: API エラー時は当該チャンクをスキップして処理継続
    - スコアは ±1.0 にクリップ
    - DuckDB への書き込みは冪等（DELETE→INSERT、トランザクション使用）
    - テスト容易性: _call_openai_api をパッチで差し替え可能
  - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）
    - マクロ記事抽出のためのキーワードリスト実装
    - LLM 呼び出しの独立実装（news_nlp と内部関数を共有しない設計）
    - API エラーやパース失敗時は macro_sentiment=0.0 を使うフェイルセーフ
    - レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - リトライ・バックオフ対応、JSON レスポンスの検証、スコアクリップ等を実装

- データ基盤（src/kabusys/data）
  - ETL パイプラインインターフェースの公開（ETLResult の再エクスポート）
  - ETL 実行結果を表現する dataclass: ETLResult（保存件数・品質問題・エラー情報など）
  - pipeline モジュール（差分取得・保存・品質チェックの設計方針・ユーティリティ）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などのユーティリティ実装
    - market_calendar が存在しない場合は曜日（平日=営業日）でフォールバック
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新、バックフィル・サニティチェック実装
    - 最大探索日数やバックフィル日数などの安全パラメータを設定
  - DuckDB ユーティリティ（テーブル存在確認・最大日付取得など）

- リサーチ（src/kabusys/research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数（calc_momentum, calc_volatility, calc_value）
    - prices_daily / raw_financials のみを参照し、外部 API にアクセスしない設計
    - 200 日 MA、ATR、出来高・売買代金の移動平均などを計算
    - データ不足時は None を返す（堅牢性重視）
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）
    - IC（Spearman）計算 calc_ic（ランク化、3 銘柄未満は None）
    - 統計サマリー factor_summary（count/mean/std/min/max/median）
    - rank ユーティリティ（同順位は平均ランク）
  - data.stats からの zscore_normalize を再エクスポート

### 変更・設計上の注意 (Changed / Notes)
- ルックアヘッドバイアス対策
  - AI 関連・リサーチ関連の関数は datetime.today() / date.today() を内部で参照しない設計。必ず caller が target_date を渡す必要がある。
  - DB クエリは target_date 未満 / 以前などの条件を厳密に指定し、未来データが混入しないようにしている。
- トランザクションと冪等性
  - ai_scores / market_regime / market_calendar 等への書き込みは DELETE→INSERT を行いトランザクションで囲むことで冪等性を確保。
  - DuckDB の executemany に関する互換性（空リスト不可）を考慮した実装になっている。
- OpenAI API 呼び出し
  - gpt-4o-mini を想定（MODEL 定数）
  - JSON Mode の response_format を使い、レスポンスは厳密な JSON を期待するが、前後ノイズが混ざるケースに備えたパースの回復処理あり
  - テストのため API 呼び出しを差し替えられるように内部の呼び出し関数が分離されている
- 環境変数パースの堅牢化
  - クォート内のエスケープ、インラインコメントの取り扱い、export プレフィックス対応など .env 形式の多様性に対応

### 修正・堅牢化 (Fixed)
- API 呼び出し失敗時のフェイルセーフ動作を明確化
  - score_news, score_regime は API 失敗時に例外を投げず部分スキップまたは 0.0 を使って継続する実装（可用性優先）
- OpenAI SDK の APIError 取り扱いで将来の SDK 変更に耐える取得方法（getattr で status_code を安全に参照）
- JSON パース失敗時のリカバリ実装（最外側の {} を抽出して再パースを試みる）

### 既知の制約・注意点 (Known limitations)
- DuckDB を前提としているため、実行には DuckDB の環境が必要
- J-Quants / kabu ステーション API との連携部分（jquants_client 等）は外部依存がある想定
- OpenAI API キー未設定時は ValueError が発生する（呼び出し側でキーを渡すか OPENAI_API_KEY を設定する必要あり）
- 一部ソース（例: pipeline の _adjust_to_trading_day 等）は提供コードの途中で切れているため、実装が続く想定（本リリースでは主要機能は網羅済み）

### セキュリティ (Security)
- OpenAI API キーは必須（score_news / score_regime）。キーの扱いは環境変数経由を想定。
- .env の自動読み込みで OS 環境を上書きしない保護機構を導入（protected set により上書き不可）。

---

今後のセクション（Unreleased）では、追加予定の機能・改善点（strategy 実装、実運用向け execution / monitoring 機能の拡充、J-Quants クライアントの堅牢化など）を追記していく想定です。