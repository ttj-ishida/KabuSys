# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

記載ルール:
- バージョン番号はパッケージ内の __version__（現在 0.1.0）に合わせています。
- 日付は本リリースの作成日です（YYYY-MM-DD）。

## [Unreleased]

- 今後のリリース予定の変更点や検討中の改善点をここに記載します。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買プラットフォームのコア機能群を提供します。主にデータ取得・ETL、マーケットカレンダー管理、要因（ファクター）計算、ニュース NLU（LLM ベース）によるセンチメント評価、そして市場レジーム判定を含みます。

### Added
- パッケージ構成
  - kabusys パッケージの初期実装を追加。
  - サブパッケージ公開: data, research, ai, execution, strategy, monitoring（__all__ で公開）。

- 設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env パース機能を強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、コメント判定の細かいルールに対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途）。
  - Settings クラスを実装し、アプリケーションで使用する主要設定をプロパティとして提供（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等）。
  - 環境値検証（KABUSYS_ENV の有効値、LOG_LEVEL の有効値）と必須値取得時の ValueError を提供。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（data.pipeline）と ETL 結果データクラス ETLResult を実装（取得件数・保存件数・品質問題等の集約）。
  - calendar_management: JPX マーケットカレンダー管理モジュールを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを追加。
    - market_calendar が未取得のときは曜日ベースでフォールバックする堅牢な設計。
    - 夜間の calendar_update_job を実装（J-Quants API から差分取得し冪等的に保存、バックフィル、健全性チェックを含む）。
  - ETL 側のユーティリティ: _get_max_date, _table_exists 等の DB ヘルパーを実装。
  - ETLResult.to_dict により品質問題をシリアライズ可能に。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を算出、ai_scores テーブルへ保存する機能を実装。
  - タイムウィンドウ定義（JST 基準で前日 15:00 〜 当日 08:30）とその UTC 変換を提供（calc_news_window）。
  - 入力テキスト長や記事数に対するトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）の実装でトークン肥大化対策。
  - API 呼び出しでのリトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。
  - OpenAI の JSON Mode 応答を堅牢にパース・検証（results 配列・コード整合性・数値変換・クリッピング）。
  - 部分失敗に備え、書き込みは該当銘柄のみ DELETE→INSERT することで既存スコアを保護（DuckDB の executemany の空リスト制約を考慮）。

- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装（score_regime）。
  - DuckDB からのデータ取得はルックアヘッドバイアスを防ぐため target_date 未満のデータのみを使用。
  - マクロニュース抽出（キーワードフィルタ）→ LLM（gpt-4o-mini）評価の流れを実装。記事が無ければ LLM コールを行わず macro_sentiment=0.0 を採用するフォールバック。
  - OpenAI API 呼び出しのリトライ/エラーハンドリングを実装（RateLimit, Connection, Timeout, 5xx 等）。
  - DB への書き込みは BEGIN / DELETE（当該日）/ INSERT / COMMIT で冪等性を確保。失敗時は ROLLBACK を試みる。

- リサーチ（kabusys.research）
  - factor_research: モメンタム、ボラティリティ（ATR 等）、バリュー（PER/ROE）等の定量ファクター計算を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグや移動平均を算出。
    - データ不足時は None を返す等の安全設計。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリ非依存で標準ライブラリのみを使用。
    - rank は同順位の平均ランク処理を実装し、丸め誤差対策を組み込み。

- 共通
  - DuckDB を主要な分析 DB として利用する一貫した実装。
  - OpenAI クライアント生成は api_key を引数で上書き可能（テスト容易化）。
  - テスト用フック: _call_openai_api 等の内部関数はテスト時に patch して差し替え可能。
  - ロギング（logger）を多用し、警告や info による運用情報・フォールバック理由を出力。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし（ただし各モジュールで安全側のフォールバック/エラーハンドリングを多数実装）。

### Security
- API キー等の機密情報は環境変数から取得する設計。自動 .env ロード時に OS 環境変数は保護（protected set）され、上書きを抑止する挙動を採用。
- KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テストや CI 向け）。

### Notes / Known limitations
- OpenAI API 依存部分は外部ネットワークに依存するため、API 利用料・レート制限・モデルの挙動に注意が必要。
- ai_scores / market_regime 等の書き込みは DuckDB を前提としている点に注意（別 DB 利用時は互換性検討が必要）。
- 現バージョンでは PBR・配当利回りなどのバリューファクターは未実装（calc_value 注記参照）。
- strategy / execution / monitoring パッケージは公開されているが、本 CHANGELOG のコード差分からは実装の詳細が確認できない（別途リリースで追記予定）。

---

今後のリリースでは、実運用向けの監視・フォールバック強化、より多様なファクター追加、CI向けモックサポート、ドキュメント・型注釈の拡充などを予定しています。