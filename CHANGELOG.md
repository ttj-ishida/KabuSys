CHANGELOG
=========

この変更履歴は「Keep a Changelog」準拠の形式で記載しています。  
コードベースから推測できる機能追加・設計方針・不具合修正などを日本語でまとめています。

※ 日付はリリース想定日（本出力日）を使用しています。実際のリリース日やバージョン管理に合わせて調整してください。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-03
--------------------

初回リリース。日本株自動売買／データ基盤向けのコアライブラリ群を追加しました。
主要な追加点・設計方針は以下の通りです。

Added
- パッケージ基本
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, research, ai, ...）を公開。
- 設定管理（kabusys.config）
  - .env ファイルや環境変数からの設定読み込みを実装。
  - 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env のパース機能を強化:
    - export KEY=val 形式への対応
    - シングル／ダブルクォート内のエスケープ処理対応
    - インラインコメント対応（クォートの有無に応じた扱い）
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS環境変数を保護するため protected set を使った上書き制御。
  - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などをプロパティで取得可能。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL など）を実装。
- データ（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を休場）を使用。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル・健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー集約用）。
    - ETL パイプライン骨組み（差分取得、保存、品質チェック）実装方針を反映。
    - jquants_client および quality モジュールとの連携を想定した I/O。
- 研究（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200日移動平均乖離を計算。
    - calc_volatility: 20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（PBR 等は未実装）。
    - 全関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) ベースの辞書リストを返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ランク相関（Spearman の ρ）を計算する機能を実装（欠損・同順位・最小データ数の処理含む）。
    - rank / factor_summary: ランク変換・基本統計量（count/mean/std/min/max/median）を提供。
    - pandas 等に依存せず、標準ライブラリ + DuckDB 性能を前提に実装。
- AI（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を結び、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを取得し ai_scores に書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算（calc_news_window）。
    - バッチ処理（1 コール最大 20 銘柄）、1 銘柄あたりの最大記事数／文字数制限、JSON Mode を使った厳格パース。
    - 429 / 接続障害 / タイムアウト / 5xx などを指数バックオフでリトライする堅牢化。
    - レスポンスバリデーション（results 配列、code の正規化、数値チェック、スコアの ±1.0 クリップ）。
    - 部分失敗に配慮した DB 書き込み（対象コードのみ DELETE → INSERT を実行）。
  - regime_detector:
    - ETF (1321) の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime テーブルに日次判定を書き込む処理を実装。
    - マクロニュースは news_nlp の calc_news_window を再利用して抽出、LLM には gpt-4o-mini を使用（JSON 出力期待）。
    - LLM 呼び出し失敗時のフォールバック（macro_sentiment = 0.0）やリトライ／エラー種別別の扱いを明確化。
    - DB 書き込みは冪等に実行（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
- 設計上の安全措置・方針
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today() / date.today() を直接参照しない設計。target_date を明示的に受け取り、DB クエリは排他条件（date < target_date / date = target_date 等）を厳密に扱う。
  - API フェイルセーフ: OpenAI 等の外部 API 失敗時は例外を投げずにフォールバック動作（0.0 スコアやスキップ）して処理を継続する方針を採用。
  - DB 書き込みの冪等性確保: 部分失敗時に既存データを不必要に削除しない（対象コードに限定して DELETE → INSERT）。
  - DuckDB 互換性配慮: executemany の空リスト禁止など、既知の DuckDB 制約に配慮した実装。
- ロギング
  - 各モジュールで詳細な情報ログ・警告ログ・例外ログを付与して運用時デバッグをしやすくしている。

Changed
- （初版のため過去からの変更はなし。実装上の設計決定と動作仕様を明記。）

Fixed
- .env パーサーの挙動改善（クォート内エスケープ、export プレフィックス、インラインコメントの扱いなど）により現実の .env ファイル互換性を向上。

Security
- 環境変数の自動ロード時に既存 OS 環境（プロセス環境）を protected set として上書きから保護する実装を導入。

Known limitations / Notes
- OpenAI SDK（OpenAI.Client）および DuckDB がランタイム依存です。実行環境にインストールが必要です。
- jquants_client, quality モジュールなどは外部実装を想定しており、本コードはそれらとのインターフェースを前提としています。
- news_nlp/regime_detector は gpt-4o-mini の JSON Mode 出力を前提としており、モデル出力の不確実性に対して堅牢化（パース復元・フォールバック）を行っていますが、運用時はモニタリングが必要です。
- PBR や配当利回りなど一部バリューファクターは未実装。

Migration notes
- 既存システムから導入する場合:
  - DuckDB に期待されるテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が必要です。
  - 環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。
  - 自動 .env 読み込みはプロジェクトルート検出に依存するため、パッケージ配布後やテスト環境で問題がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

貢献・ライセンス
- （このドキュメントはコード内容から推測して作成した CHANGELOG です。実際の貢献者情報やライセンス情報はリポジトリの該当ファイルを参照してください。）