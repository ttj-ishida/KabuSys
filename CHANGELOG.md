CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従い、セマンティックバージョニングを使用します。
<!-- 初回リリース: 0.1.0 -->

[Unreleased]
------------

- （今後の変更をここに記載）

0.1.0 - 2026-04-01
------------------

Added
- 初回リリース。パッケージ名: kabusys、バージョン 0.1.0 を定義。
- パッケージの公開シンボルを定義:
  - kabusys.__all__ に ["data", "strategy", "execution", "monitoring"] を登録。
- 環境設定管理 (kabusys.config):
  - .env / .env.local 自動ロード機能を実装（優先順位: OS環境変数 > .env.local > .env）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルのパース機能を実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理を考慮）。
  - override と protected（OS 環境変数保護）オプション付きの .env 読み込み。
  - 必須環境変数チェック用の _require ユーティリティ。
  - Settings クラスを公開:
    - J-Quants / kabuステーション / Slack / DB / 監視 / システム関連のプロパティ群（例: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, pid_file_path, cpu_threshold_pct 等）。
    - KABUSYS_ENV 値検証（development / paper_trading / live のみ許容）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のショートカットプロパティ。
- AI モジュール (kabusys.ai):
  - ニュース NLP (kabusys.ai.news_nlp):
    - ニュース収集ウィンドウ計算 (calc_news_window) を実装（JSTベース -> UTC ナイーブ datetime 出力）。
    - raw_news / news_symbols から銘柄別に記事を集約する処理を実装（_fetch_articles）。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメントスコアリング (score_news) を実装:
      - 銘柄ごとの記事集約、1銘柄あたり最大記事数・文字数トリム。
      - 最大 20 銘柄/チャンク単位での API 呼出し。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ付きリトライ。
      - レスポンス検証（JSON 抽出、results 配列、code/score の検証、未知コードは無視）。
      - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等書き込み（DELETE → INSERT、部分失敗で既存スコアを保護）。
      - テスト用に OpenAI 呼出しを差し替え可能（_kabusys.ai.news_nlp._call_openai_api をモック可）。
  - レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321 の 200 日移動平均乖離とマクロニュース（LLM）を組合わせ、日次市場レジーム（bull/neutral/bear）を算出 (score_regime)。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からマクロキーワードで抽出（最大 20 記事）。
    - OpenAI 呼出しは独立した内部実装を使用（news_nlp と内部関数共有を避ける設計）。
    - API 失敗・JSON パース失敗時は macro_sentiment を 0.0 にフォールバックして継続（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼出し関数はテストで置換可能。
- Research モジュール (kabusys.research):
  - factor_research:
    - モメンタム（1M/3M/6M）、200日移動平均乖離の計算 (calc_momentum)。
    - ATR（20日）や相対ATR、20日平均売買代金、出来高比率を計算するボラティリティ/流動性指標 (calc_volatility)。
    - 財務データ（raw_financials）から PER/ROE を計算するバリューファクター (calc_value)。
    - 全て DuckDB の prices_daily / raw_financials を参照し、外部 API へはアクセスしない設計。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns)、Spearman（ランク）による IC 計算 (calc_ic)。
    - rank（同率は平均ランク）、factor_summary（count/mean/std/min/max/median）等のユーティリティを実装。
    - pandas 等外部依存を用いず標準ライブラリで実装。
  - 研究向けに kabusys.data.stats.zscore_normalize を再エクスポート。
- Data モジュール (kabusys.data):
  - market_calendar 管理 (calendar_management):
    - 営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB の market_calendar を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等保存（バックフィル・健全性チェック付き）。
  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスを実装（取得/保存件数、品質問題、エラー一覧を保持）。
    - 差分フェッチ、保存（jquants_client 経由での冪等保存）、品質チェックの設計に準拠したインターフェースを提供。
    - ETLResult.to_dict() による品質問題のシリアライズを実装。
  - jquants_client と quality へ依存する実用的なデータ更新フローに対応。
- DuckDB を主要な分析 DB として利用する実装（各モジュールで DuckDB 接続を受け取る設計）。
- ロギングを各モジュールに導入し、処理途中の情報や警告・例外を記録。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Deprecated
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照する仕様。デフォルトでコード内にハードコードしない設計。

Design / Implementation Notes（設計上の注記）
- ルックアヘッドバイアス対策:
  - 各種処理は datetime.today()/date.today() を直接参照しない。target_date を明示して外部から与える設計。
- フェイルセーフ方針:
  - LLM 呼出し失敗時は例外を上位へ投げず安全側の既定値（0.0）で継続する実装を採用（運用継続性重視）。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- テスト容易性:
  - OpenAI 呼出しを内部関数として分離し、unittest.mock.patch で差し替え可能にしている。
- DuckDB のバージョン互換性:
  - executemany に空リストを渡せない (DuckDB 0.10 の制約) ことを考慮して条件分岐を実装。
- .env パーサは POSIX 風の形式（export, quotes, inline comments）に対応する堅牢な実装。

Known issues / TODO
- pipeline._get_max_date 関数の末尾が不完全（ソース末尾の "return date.fro" のような切れたコードが存在）。このままだと実行時にエラーになる可能性があるため修正が必要。
- strategy / execution / monitoring パッケージはトップレベルで公開シンボルに含まれているが、本スナップショットでは該当実装ファイルが不足している（または省略）。実行環境でこれらを使用するには追加実装が必要。
- 一部外部クライアント（jquants_client 等）の実装は別モジュールに依存するため、実際の運用にはそれらの接続実装とテーブルスキーマ整備が必要。
- OpenAI 呼出しは gpt-4o-mini を想定しているが、現行の SDK/API 変更に伴う互換性確認・テストが必要。

参考: 主要参照テーブル
- prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などを各モジュールが参照・更新する設計になっています。実行前に DB スキーマを整備してください。

---

作成元: ソースコード解析に基づく初期リリースの変更ログ（自動生成・推測を含む）。必要に応じて運用実績や追加実装を反映して更新してください。