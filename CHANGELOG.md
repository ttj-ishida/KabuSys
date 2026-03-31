CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
---

[0.1.0] - 2026-03-31
--------------------

Added
- 初回リリース。日本株自動売買プラットフォーム "KabuSys" の基本コンポーネントを追加。
- パッケージのバージョンを設定（kabusys.__version__ = "0.1.0"）。

- 設定・環境管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装
  - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、コメント処理などをサポート
  - 環境変数の保護（既存 OS 環境変数を上書きしない / .env.local で上書き可能）実装
  - Settings クラスを公開（settings オブジェクト）。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live 検証）、LOG_LEVEL 検証
    - ヘルパープロパティ: is_live, is_paper, is_dev
  - 必須環境変数未設定時は ValueError を発生させる _require 実装

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約
    - OpenAI（gpt-4o-mini）の JSON mode を用いたバッチ評価（最大バッチサイズ 20 銘柄）
    - レスポンスのバリデーションとスコアクリップ（±1.0）
    - エラー時のリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に他銘柄のスコアを保護）
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す
    - calc_news_window(target_date) により JST ベースのニュース収集ウィンドウを計算（look‑ahead バイアスに配慮）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して
      日次で market_regime テーブルにレジーム評価を保存
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント算出（記事がない場合は LLM 呼び出しをスキップ、API 失敗時は 0.0 にフォールバック）
    - レスポンス取得に関するリトライ・エラーハンドリングを実装
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す
    - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。失敗時は ROLLBACK。

  - 実装方針・共通点
    - OpenAI クライアント呼び出しはテストで差し替え可能な内部関数として実装
    - datetime.today()/date.today() を直接参照せず、引数で与えた target_date のみを使う設計（ルックアヘッドバイアス回避）

- データモジュール（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装
      - J-Quants API から差分取得し market_calendar テーブルへ冪等保存
      - バックフィル、健全性チェック（将来日付異常時のスキップ）を実装
    - 営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動
      - 最大探索日数による無限ループ防止
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）
      - ETL 実行結果の集約（取得・保存件数、品質チェック、エラー情報など）
      - has_errors / has_quality_errors / to_dict ヘルパー
    - 差分更新、バックフィル、品質チェックの方針を実装する基盤ロジック（細部は jquants_client / quality モジュールに依存）
  - ユーティリティ: DuckDB テーブル存在チェックや最大日付取得などの内部関数を実装

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 乖離などを計算
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、平均売買代金、出来高比率などを計算
    - calc_value(conn, target_date): raw_financials と価格を組み合わせて PER/ROE を算出
    - DuckDB の SQL ウィンドウ関数を利用して効率的に計算
    - 結果は (date, code) をキーとした dict のリストで返す
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン計算（デフォルト [1,5,21]）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算
    - rank(values): 同順位は平均ランクとするランク変換ユーティリティ
    - factor_summary(records, columns): 各カラムの count/mean/std/min/max/median を計算
  - 研究用途の関数群を再エクスポート（kabusys.research.__all__ にまとめられている）

Changed
- （初回リリースのため履歴は追加のみ）

Fixed
- （初回リリースのため履歴は追加のみ）

Security
- OpenAI API キーや他の機密情報は Settings 経由で必須チェックを行い、未設定時は明示的なエラーとすることで誤作動を防止

Notes / 実装上の注意
- DuckDB を主要な永続化レイヤーとして想定（関数は DuckDB 接続オブジェクトを引数に取る）
- OpenAI SDK（chat completions / JSON mode）に依存。テスト容易化のため内部 API 呼び出しを差し替え可能に設計
- LLM 呼び出し失敗時はフェイルセーフによりスコアに 0 を使う、または当該チャンクをスキップする方針
- 日時処理はすべて timezone-naive な date/datetime を用い、JST ↔ UTC のウィンドウ変換を明確に行う

今後のリリースに向けた検討事項（例）
- jquants_client の実装と統合テスト
- 詳細な品質チェック（quality モジュール）の充実と ETL ワークフローの自動化
- モデル・プロンプト改善、LLM の結果安定化（複数モデル比較やフェイルオーバー）
- ドキュメントの充実（API リファレンス、運用手順）

---

著者: KabuSys 開発チーム (コードベースから推測して作成)