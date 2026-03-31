CHANGELOG
=========

すべてのリリースは Keep a Changelog の形式に準拠します。
このファイルは日本語で記載しています。

[Unreleased]
------------

- （現時点の最新版は 0.1.0 のため Unreleased に変更点はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルートおよび公開API:
    - パッケージバージョン: 0.1.0
    - __all__: ["data", "strategy", "execution", "monitoring"]

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探すため、CWD に依存しない。
  - 強力な .env パーサ:
    - コメント、export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープに対応。
    - クォートなし行の inline コメント処理を文脈に応じて実施。
  - .env 読み込み時の上書き制御:
    - override フラグと protected キーセット（OS 環境変数保護）をサポート。
  - Settings クラス:
    - アプリケーション設定をプロパティ経由で提供（J-Quants / kabu API / Slack / DB パス / 監視しきい値 / 環境・ログレベル判定等）。
    - 必須設定は _require で明示的に ValueError を送出（未設定時）。
    - KABUSYS_ENV と LOG_LEVEL の検証とヘルパー is_live / is_paper / is_dev を提供。
    - デフォルト値を持つプロパティ（KABU_API_BASE_URL, DUCKDB_PATH 等）。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント ai_score を計算。
    - タイムウィンドウ: JST 前日 15:00 ～ 当日 08:30（内部は UTC naive で計算、calc_news_window を提供）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode を使った厳密な JSON レスポンス期待と検証ロジックを実装。
    - 再試行ロジック: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。
    - フェイルセーフ: API 失敗やパース失敗時は当該チャンクをスキップし他チャンクは継続。空の場合は 0 件として終了。
    - スコアは ±1.0 にクリップ。
    - 書き込みは ai_scores テーブルに対して冪等（DELETE → INSERT）で実施。部分失敗時に既存スコアを保護する設計。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し日次で 'bull' / 'neutral' / 'bear' 判定を行う。
    - マクロ記事抽出はキーワードベースで titles を取得（最大 20 件）。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない設計）。
    - リトライ・フェイルセーフ: API の連続失敗やパース失敗は macro_sentiment=0.0 にフォールバックして続行。
    - レジーム算出後は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。エラー時は ROLLBACK を試行し例外を上位へ伝播。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満のデータのみ使用。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（祝日・半日取引・SQ）を管理するユーティリティ。
    - 営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバック。
    - next/prev/get_trading_days は DB 登録値優先・未登録は曜日フォールバックで一貫した結果を返す。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィル、健全性チェック（未来日付の異常検知）を実装。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開（ETL 実行結果の構造化保存・to_dict を提供）。
    - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールを利用）。
    - DuckDB を想定したテーブル存在チェックや最大日付取得ユーティリティを提供。
    - 設計方針として「営業日単位での差分取得」「部分失敗時も可能な限り保存」「品質チェックは呼び出し元が判定する」ことを採用。

- Research モジュール (kabusys.research)
  - ファクター計算と特徴量探索を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の乖離）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR・流動性指標）
    - calc_value: PER（price / EPS）、ROE（raw_financials からの最新財務データ使用）
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）に対する将来リターンを一括クエリで取得
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）計算。3 銘柄未満は None を返す。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにする方法でランク化。
    - zscore_normalize は kabusys.data.stats から再エクスポート
  - 実装方針:
    - DuckDB を前提に SQL と Python を組み合わせて高効率に計算。
    - lookahead バイアス防止のため日時取得は外部から与える target_date ベースでの計算。

Other notable points
- DuckDB をメインのローカル分析 DB として想定。多くの操作は DuckDB 接続（DuckDBPyConnection）を引数に取る。
- OpenAI SDK（OpenAI クラス）を利用し、モデル gpt-4o-mini / JSON Mode を前提に実装。
- ログ出力と警告を多用し、安全に失敗から回復する設計。外部 API の障害があっても致命的に停止しないフォールバックを備える。
- テスト支援:
  - OpenAI 呼び出し関数（_call_openai_api）を unittest.mock.patch で差し替え可能にしている箇所があり、API 呼び出しのモックが容易。

Changed
- 初回リリースのため履歴なし。

Fixed
- 初回リリースのため履歴なし。

Security
- 初回リリースのため既知のセキュリティ修正はなし。
- 注意: OpenAI API キーや Slack トークン等の機密値は環境変数で管理すること。settings._require により必須項目は明示される。

Required / Recommended 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (AI 機能使用時必須)
- KABUSYS_ENV (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH 等はデフォルトパスあり

マイグレーション／移行メモ
- 既知の互換性破壊はありません（初回リリース）。
- 今後のリリースでは Settings のプロパティ追加や .env の仕様変更、DB スキーマ変更があり得るため、ETLResult.to_dict 等を監査ログに利用することを推奨します。

貢献・テストに関する備考
- AI 呼び出しのテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env の自動ロードを抑制し、テスト用環境変数を注入してください。
- OpenAI 呼び出しは内部関数をパッチすることで副作用なくテスト可能です（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。

---
上記はコードベースの内容から推測してまとめた CHANGELOG です。必要であれば、各モジュールごとの詳細な変更点や使用例、既知の制限事項を追記します。