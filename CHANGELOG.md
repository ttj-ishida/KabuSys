# Changelog

全ての notable な変更履歴をここに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。

最新変更は常にトップに記載します。

## [0.1.0] - 2026-03-27

Added
- 初回リリース: KabuSys 日本株自動売買／データ研究基盤のコア実装を追加。
  - パッケージ情報
    - src/kabusys/__init__.py によるバージョン管理（`__version__ = "0.1.0"`）と主要サブパッケージの公開 (`data`, `strategy`, `execution`, `monitoring`)。
  - 設定管理
    - src/kabusys/config.py:
      - .env ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを提供。プロジェクトルートの自動検出は `.git` または `pyproject.toml` を基準に行う。
      - `.env` と `.env.local` の優先度制御（`.env.local` が上書き）、OS 環境変数の保護（上書き不可）をサポート。
      - 単一行パーサ `_parse_env_line` は `export KEY=val`、引用符付き値、インラインコメントの扱いなどに対応。
      - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。
      - `Settings` クラスにより J-Quants / kabuステーション / Slack / DB パス / 環境モード（development/paper_trading/live）/ログレベルの取得・検証を実装。未設定の必須環境変数は例外で明示。
  - AI (ニュース NLP / レジーム判定)
    - src/kabusys/ai/news_nlp.py:
      - raw_news と news_symbols を基にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を扱うユーティリティ `calc_news_window` を提供。
      - API 呼び出しはバッチサイズ（デフォルト20銘柄）で実行し、429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
      - レスポンスは厳密にバリデーション（JSON 抽出、キー/型チェック、未知コードの無視、数値チェック）し、スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。
      - テスト容易性を考慮し、OpenAI 呼び出し関数 `_call_openai_api` を patch 可能に設計。
      - API キー解決は引数または環境変数 `OPENAI_API_KEY`。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ保存。
      - ma200 比率算出は target_date 未満のデータのみを使用し、データ不足時は中立値（1.0）にフォールバックしてフェイルセーフ化。
      - マクロキーワードで raw_news をフィルタし、最大 N 記事を LLM に送信して macro_sentiment を算出。LLM／API エラー時は macro_sentiment=0.0 で継続。
      - OpenAI 呼び出しは news_nlp とは別実装とし、モジュール結合を低く抑える設計。
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターンで実装。書き込み失敗時は ROLLBACK を試み、失敗の際は警告ログを出力。
  - Data（ETL / カレンダー）
    - src/kabusys/data/calendar_management.py:
      - market_calendar テーブルを前提にした営業日判定ユーティリティ群を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - DB データが不完全な場合は曜日ベース（土日）でフォールバックする一貫したロジックを採用。
      - 夜間バッチ更新ジョブ `calendar_update_job` を実装し、J-Quants クライアントから差分取得 → 保存（バックフィル／健全性チェックを含む）を行う。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
      - ETL パイプラインの骨子を実装（差分更新、idempotent 保存、品質チェックの呼び出し）。
      - `ETLResult` データクラスを導入し、取得件数・保存件数・品質問題・エラー概要を集約。`to_dict()` によるシリアライズを提供。
      - 差分取得におけるバックフィル処理やカレンダー先読みを考慮した設計（デフォルト backfill 日数等）。
      - src/kabusys/data/etl.py は ETLResult を再エクスポート。
    - data モジュール内で jquants_client / quality などのクライアント層を利用する想定。
  - Research（因子計算・特徴量探索）
    - src/kabusys/research/factor_research.py:
      - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR）および流動性指標（平均売買代金等）、バリュー（PER, ROE）を DuckDB の SQL と Python を組み合わせて計算する関数を提供（calc_momentum / calc_volatility / calc_value）。
      - 大量データスキャン範囲を適切に限定し、欠損・データ不足時に None を返す設計。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランキング変換（rank）、統計サマリー（factor_summary）を提供。
      - 外部ライブラリに依存せず、標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py で主要関数を公開。
  - 共通的な設計方針・品質面
    - ルックアヘッドバイアス防止のため、各モジュールで datetime.today()/date.today() を直接参照する処理を避け、呼び出し側から target_date を受け取る設計を徹底。
    - OpenAI など外部 API 呼び出しはエラー耐性（フォールバック値・ログ出力・リトライ/バックオフ）を重視し、ETL/AI 処理で部分失敗があっても他データに影響を最小化する方針。
    - DuckDB を主要なローカル DB として利用。テーブル存在チェックや executemany に関する互換性に配慮した実装（空パラメータ回避等）。
    - DB への書き込みは可能な限り冪等に実装（DELETE→INSERT、ON CONFLICT 設計を想定）。
    - ロギングを多用し、警告・情報ログでフェイルセーフ挙動や重要イベントを記録。
  - テストと拡張性
    - OpenAI 呼び出し関数はモック差し替えを想定しており、ユニットテストで容易に置き換え可能。
    - 設定読み込みの自動化はテスト環境向けに無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - 多くの内部関数（例: _parse_env_line, _validate_and_extract, calc_news_window など）が単体で利用・テストできるように設計。

Notes
- 本リリースは基盤となる機能を包含する初期版です。今後のリリースで以下を予定:
  - 追加の戦略ロジック（strategy パッケージの実装拡張）
  - 実売買・発注ロジック（execution パッケージ）
  - 監視・アラート機能（monitoring パッケージ）
  - ドキュメント整備・使用例追加
  - テストカバレッジ拡充と CI ワークフロー整備

---
出典: ソースコード（src/kabusys 以下）から推測して記載。実際のリリースノートでは変更差分に基づく明示的な差分記録（旧バージョンとの差分）を併記してください。