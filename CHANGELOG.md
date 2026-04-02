# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

※ この CHANGELOG はリポジトリ内のソースコードから機能・設計・フェイルセーフ挙動を推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-02

初回リリース。本リリースでは日本株自動売買／データ基盤／リサーチ／AI 補助機能の基盤モジュール群を実装しています。

### Added
- パッケージ初期化
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント扱い（'#' の条件付き）に対応。
  - 環境設定ラッパー Settings を提供。J-Quants / kabu API / Slack / DB パス /監視しきい値 / 実行環境（development, paper_trading, live）などのプロパティを用意。
  - 必須環境変数未設定時は明確な ValueError を送出する _require を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄毎のセンチメント（-1.0〜1.0）を算出・ai_scores テーブルへ書き込み。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）と、1 銘柄当たりの記事数制限／文字数トリム（最大記事数・最大文字数）。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。失敗時は該当チャンクをスキップして処理継続するフェイルセーフ挙動。
    - API レスポンスの厳密なバリデーションとスコアクリップ（±1.0）。
    - calc_news_window(target_date) を公開。JST ベースで前日 15:00 ～ 当日 08:30 相当を UTC naive datetime で返す（DB 比較用）。
    - score_news は書き込んだ銘柄数を返す。API キーは引数または OPENAI_API_KEY 環境変数から取得。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロキーワードによる raw_news フィルタ、最大記事数制限、OpenAI 呼び出し（gpt-4o-mini）、リトライとフェイルセーフ（API 失敗時 macro_sentiment = 0.0）。
    - レジームスコア合成式（クリップ）と閾値に基づくラベリング。結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API キーは引数または OPENAI_API_KEY 環境変数から取得。未設定時に ValueError を送出。

- Data / ETL（kabusys.data）
  - ETL 結果クラス（ETLResult）を定義して pipeline モジュール経由で再エクスポート。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存（jquants_client 経由で idempotent 保存を想定）、品質チェック（quality モジュール）を実装する計画・骨格。
    - backfill 等の設定と品質問題の収集方針（Fail-Fast ではなく呼び出し元が判断する設計）。
    - DuckDB テーブル存在チェックや最大日付取得等のユーティリティを実装（ETLResult により処理結果を構造化）。

  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業時間判定（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - カレンダーデータ未取得時は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に更新する夜間バッチ実装（バックフィル / 正常性チェックを含む）。
    - 内部で _MAX_SEARCH_DAYS 等の保護設定を有効にし無限探索を防止。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20日 ATR）、Value（PER / ROE）および流動性指標を DuckDB SQL を用いて算出する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返す等の堅牢な挙動。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、horizons 検証と 252 日上限）、IC（Spearman ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等には依存せず標準ライブラリ + DuckDB で完結する実装方針。

### Changed
- （初回リリースのため履歴上の変更は無し）

### Fixed
- （初回リリースのため履歴上の修正は無し）

### Security
- OpenAI API キーは明示的に引数で注入可能。環境変数依存を減らす設計でテスト性と安全性を向上。

### Design / Reliability notes（設計上の重要点・フェイルセーフ）
- ルックアヘッドバイアス防止: date.today() / datetime.today() を主要処理で参照せず、すべて呼び出し元から target_date を渡す設計。
- OpenAI 呼び出し失敗に対しては局所的にフォールバック（macro_sentiment=0.0 等）し、処理全体を停止させないフェイルセーフを採用。
- DuckDB への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、部分失敗時にも他データを保護する実装（例: ai_scores の DELETE → INSERT を該当コードのみで行う）。
- .env パーサは細かなケース（クォート内のエスケープ、コメント、export プレフィックス）に対応し、実用上の堅牢性を重視。

### Removed / Deprecated
- なし

## 既知の注意事項 / 今後の予定
- strategy, execution, monitoring モジュールはパッケージ公開対象に含まれているが、本リリースでは該当実装や詳細は省略（追加実装・拡充予定）。
- jquants_client / quality モジュールとの連携は想定されているが、外部 API クライアントの具体実装やネットワークエラー処理方針は運用でさらに補強予定。
- テスト用フック（_call_openai_api の patch での置き換え等）を想定した設計はあるが、詳細テストカバレッジの充実が今後の課題。

-----
参考: 本 CHANGELOG はソースコード内の docstring / ロジック /定数（例: ウィンドウ定義・重み・閾値・リトライ設定等）に基づいて作成しています。