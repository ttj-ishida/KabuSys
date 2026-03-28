CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" とセマンティックバージョニングを想定しています。

0.1.0 - 2026-03-28
------------------

Added
- 初版リリース。日本株自動売買・データプラットフォームの基盤機能を実装。
  以下の主要コンポーネントを含みます。

- パッケージ公開 API
  - pakage root: kabusys.__version__ = 0.1.0
  - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__ に準備）

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local 自動ロード機能（プロジェクトルートは .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパースは以下に対応：
    - コメント行、空行、先頭の "export KEY=val" 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォートなしのインラインコメント（直前が空白/タブの場合のみ）
  - OS 環境変数を保護するため .env.local はデフォルトで既存環境変数を上書きしない（内部的に protected set を使用）。
  - Settings クラスで主要設定をプロパティとして提供（必須項目は _require により未設定時に ValueError を送出）。
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - KABUSYS_ENV の有効値: development / paper_trading / live（無効値は例外）
    - LOG_LEVEL の有効値チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management)
    - market_calendar を参照した営業日判定（is_trading_day、is_sq_day、next_trading_day、prev_trading_day、get_trading_days）。
    - DB 登録値を優先、未登録日は曜日ベースのフォールバック（休日/週末扱い）。
    - カレンダー夜間更新ジョブ (calendar_update_job) による J-Quants からの差分取得・冪等保存と健全性チェック / バックフィル機能。
    - 最大探索日数やバックフィル日数等の安全装置を実装。
  - ETL パイプライン用ユーティリティ (pipeline, etl)
    - ETLResult dataclass による ETL 実行結果の集約（品質問題リスト / エラーメッセージ等を含む）。
    - 差分フェッチ、バックフィル、品質チェックの方針を実装するための基礎関数群。
    - DuckDB 周りの互換性考慮（テーブル存在チェック、MAX 日付取得ユーティリティ）。
    - jquants_client と quality モジュールとの連携を想定（fetch/save 呼び出しポイントを準備）。

- AI / ニュース・NLP (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp)
    - raw_news と news_symbols を基に対象ウィンドウ（前日15:00 JST〜当日08:30 JST）を計算する calc_news_window を実装。
    - 銘柄ごとに記事を集約し（最大記事数・最大文字数でトリム）、バッチ（最大20銘柄）で OpenAI Chat API（gpt-4o-mini, JSON mode）へ送信。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・code/score の存在確認、未知コード無視、スコアを ±1.0 にクリップ）。
    - DuckDB の executemany 空リスト制約を考慮して部分置換（DELETE → INSERT）で冪等的に ai_scores を更新。
    - API キー解決ロジック（引数優先、なければ環境変数 OPENAI_API_KEY）。未設定時は ValueError。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - prices_daily からの MA 計算は target_date 未満のデータのみを使用してルックアヘッドを排除。
    - raw_news からマクロキーワードで記事を抽出し、OpenAI により -1.0〜1.0 のマクロセンチメントを算出。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 冪等的に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - OpenAI 呼び出しは独立実装（news_nlp と共有しない）でテスト容易性を考慮。
    - リトライ・エラー処理・JSON パース失敗時のフォールバックを実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev を prices_daily から計算（ウィンドウ不足時は None）。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - バリュー: raw_financials の最新財務データと prices_daily を組み合わせて PER, ROE を計算（EPS が 0/欠損時は None）。
    - SQL + Python による実装で本番口座・発注 API にはアクセスしない設計。
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): target_date から各 horizon（例: 1,5,21 営業日）までのリターンを取得。horizons の入力検証あり。
    - IC 計算 (calc_ic): スピアマンのランク相関による Information Coefficient の計算（有効レコード少数時は None）。
    - ランク変換ユーティリティ (rank): 同順位は平均ランク、浮動小数丸めの考慮。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を算出。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- テスト容易性・堅牢性のための設計上の配慮
  - 時刻参照でルックアヘッドバイアスを生まないよう datetime.today()/date.today() に依存しない設計（target_date を明示的に受ける）。
  - OpenAI 呼び出し部分は内部関数をモック可能に実装（unittest.mock.patch で差し替え）。
  - API エラー時は例外を投げずにフォールバックする箇所があり（AI スコアリングなど）、運用継続性を優先。
  - DuckDB 互換性（executemany の空リスト制約、日付型処理）に対するワークアラウンドを用意。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーは環境変数または明示的引数で供給する設計。キーの出力/ログ化を行わないよう注意（実装側で秘匿に留意）。

注意事項 / マイグレーション
- OpenAI を利用する関数（score_news, score_regime）を利用する場合は OPENAI_API_KEY を環境変数に設定するか api_key 引数を渡してください。未設定の場合は ValueError が発生します。
- .env 自動読み込みはプロジェクトルート検出に依存します。配布後の挙動確認やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- DuckDB バージョンによる executemany の挙動差異を想定しているため、ai_scores などの部分置換は現行ロジックを前提に動作します。
- KABUSYS_ENV の値が許容値（development/paper_trading/live）以外だと起動時にエラーになります。CI/CD や本番環境で環境変数を確認してください。

今後の予定（例）
- strategy / execution / monitoring モジュールの具現化（現在はパッケージ公開名のみ用意）。
- テレメトリ・バックテスト用ユーティリティ、より詳細な品質チェックルールの追加。
- モデルのプロンプト改善・バッチ最適化や OpenAI レスポンスの多様性対策。

-----