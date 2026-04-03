CHANGELOG
=========

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」標準に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 変更
- Fixed: 修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース (パッケージバージョン: 0.1.0)
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エクスポート済みサブパッケージ: data, strategy, execution, monitoring
  - バージョン情報を src/kabusys/__init__.py にて公開

- 設定管理 (.env / 環境変数)
  - .env ファイルと環境変数からの設定自動読み込み機構を実装（src/kabusys/config.py）。
  - プロジェクトルート検出ロジック: __file__ を起点に .git または pyproject.toml を探索してルートを特定（CWD 非依存）。
  - .env のパース実装:
    - コメント行、export プレフィックス対応、クォート内のエスケープ処理やインラインコメントの扱いを考慮。
    - 上書き制御 (override) と OS 環境変数保護 (protected) に対応。
  - 自動ロードの無効化環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開:
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供。
    - 必須項目未設定時に明確な ValueError を送出する _require 実装。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）を提供。
    - パス系設定は pathlib.Path で返す（expanduser 対応）。
    - 監視関連の閾値やフラグ（CPU/MEM/DISK、PID/KILLフラグ等）を設定可能。

- AI（LLM）モジュール
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を銘柄毎に集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - JST 時間ウィンドウ計算（前日 15:00 ～ 当日 08:30 JST）を calc_news_window で提供。
    - 1銘柄あたりの最大記事数・文字数トリム、チャンクバッチ（最大 20 銘柄）処理、JSON mode のレスポンスバリデーション実装。
    - リトライ戦略: 429/接続断/タイムアウト/5xx に対する指数バックオフと最大リトライ。
    - レスポンス検証で未知コードや不正スコアを安全に無視。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - マクロニュース抽出（マクロキーワード）→ LLM で JSON スコア取得 → 合成スコア算出 → market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しは独立関数化（テスト容易性、モジュール結合回避）。
    - API エラーや JSON パース失敗時はフェイルセーフにより macro_sentiment=0.0 で継続。
    - リトライ処理（RateLimit, ConnectionError, Timeout, 5xx）を実装。

- データプラットフォーム（DuckDB ベース）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定ユーティリティ群:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 夜間バッチ更新 job: calendar_update_job により J-Quants API から差分取得して保存（バックフィル / 健全性チェック付き）。
    - 最大探索日数やバックフィル日数などの安全策を実装。

  - ETL / パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを公開（etl.ETLResult を再エクスポート）。
    - 差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェック（quality モジュール想定）を想定した設計。
    - バックフィル、カレンダー先読み、品質問題の収集（致命的エラーでも処理継続して情報を返す）など実務運用を意識した実装方針。

- Research（リサーチ）モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン）／200日MA乖離、Volatility（20日 ATR）／流動性（20日平均売買代金・出来高比）、Value（PER, ROE）等の計算関数を提供。
    - DuckDB 上の prices_daily / raw_financials を参照する純計算ロジック（発注等の副作用なし）。
    - データ不足時の None 扱いやログ出力、結果を (date, code) をキーとした dict リストで返す仕様。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算、ランク関数、ファクター統計サマリー等の実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
    - 計算上の安全策（horizons の検証、ties の平均ランク処理、十分小さいデータ数に対する None 返却）を備える。

- 内部ユーティリティ・設計方針
  - すべての分析・スコアリング関数は datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアスの防止）。
  - DuckDB を前提とした SQL + Python 混在の実装で高速処理を目指す。
  - 例外処理・ログ出力・冪等性（BEGIN/DELETE/INSERT/COMMIT）等、運用を見据えた堅牢性を重視。

Security
- OpenAI API キー（OPENAI_API_KEY）、J-Quants トークン（JQUANTS_REFRESH_TOKEN）、Kabu ステーションパスワード（KABU_API_PASSWORD）など機密情報は環境変数もしくは .env にて注入する設計。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト用途）。

Notes / Limitations
- J-Quants API クライアントや quality モジュール、jquants_client の具体実装は参照先に依存する想定（本差分では抽象化して利用）。
- ai モジュールは OpenAI SDK（chat completions, JSON mode）を利用する想定。API の将来の変更に備えたエラー処理を実装しているが、SDK仕様変化で追加対応が必要になる場合あり。
- DuckDB の executemany に対する空パラメータの挙動や list 型バインド挙動に配慮した実装（空リスト時は実行をスキップ）。

今後の予定（例）
- ストラテジー / 実行系の具体的実装と整合（strategy, execution モジュールの具体化）
- jquants_client の具象実装とテストカバレッジ拡充
- モニタリング UI / ランタイム運用用のエラー通知連携（LINE 連携など）
- セキュリティ監査、秘密情報のより厳格な管理（Vault 等）

（以上）