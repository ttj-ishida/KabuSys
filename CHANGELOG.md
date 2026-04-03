# CHANGELOG

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」規約に準拠しています。セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-03

初回リリース。以下の主要機能と実装方針を含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを定義（kabusys.__init__）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報: 0.1.0。

- 設定管理 (kabusys.config)
  - 環境変数および .env ファイル読み込みのユーティリティを追加。
    - .env / .env.local の自動読み込み（プロジェクトルートの検出は .git または pyproject.toml を利用）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パースは export KEY=val 形式、シングル・ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いなどを正しく処理。
    - override / protected オプションを用いて OS 環境変数を保護する挙動を実装。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。
    - J-Quants / kabuステーション / LINE / DB /監視 /システム関連の設定をプロパティで公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, PID_FILE_PATH 等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値は定義済み）。
    - is_live / is_paper / is_dev のブールプロパティを用意。

- AI ニュース解析 (kabusys.ai.news_nlp)
  - ニュース記事を OpenAI （gpt-4o-mini, JSON Mode）により銘柄単位でセンチメント化し ai_scores テーブルへ書き込む機能を実装。
  - 処理の特徴:
    - 対象ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC変換して DB と比較）。
    - 銘柄ごとに最新の記事を集約（最大 _MAX_ARTICLES_PER_STOCK、文字数制限 _MAX_CHARS_PER_STOCK）。
    - 最大 _BATCH_SIZE 銘柄ずつバッチ送信。
    - OpenAI API 呼び出しは再試行（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーション（JSON 抽出、"results" 配列、code/score の存在、スコア数値性、既知コードのみ採用）。
    - スコアは ±1.0 にクリップ。
    - 部分失敗に備え、ai_scores への書き込みは対象コードのみを DELETE → INSERT することで既存スコア保護を実現。
  - テスト用に _call_openai_api を patch して差し替え可能な設計。

- AI マーケットレジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ保存する機能を実装。
  - 処理の特徴:
    - prices_daily から ma200_ratio を算出（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - raw_news からマクロキーワードでフィルタし、LLM（gpt-4o-mini）でマクロセンチメントを評価。記事がない場合は LLM 呼び出しを行わず 0.0 を返す。
    - API 呼び出しは再試行とエラーハンドリング（RateLimit, 接続エラー, タイムアウト, 5xx 等）を実装。重大エラー時は macro_sentiment=0.0 でフォールバック。
    - スコア合成後、冪等に market_regime テーブルへ BEGIN / DELETE / INSERT / COMMIT を用いて書き込み。例外時は ROLLBACK を試行し、必要に応じて上位へ伝播。
  - テスト拡張性のため _call_openai_api と分離。

- データ管理（kabusys.data）
  - ETL パイプライン結果型 ETLResult を公開（kabusys.data.etl 経由でエクスポート）。
    - ETLResult は取得・保存レコード数、品質検査結果、エラー一覧などを含むデータクラス。
    - to_dict により品質問題を辞書化して監査ログ用に整形可能。
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックの方針を実装するためのユーティリティ群（テーブル存在確認や最大日付取得等の内部関数を含む）。
    - backfill、カレンダー先読み、品質チェックの重みづけなどの方針をコードに反映。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジックを提供。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
      - DB 登録がない場合は曜日（週末）ベースのフォールバックを利用して一貫性を維持。
      - 最大探索日数制限を設け ValueError による安全策を実装。
    - calendar_update_job を実装（J-Quants API から差分取得し保存）。
      - バックフィル、先読み、健全性チェック（過度に将来日が登録されている場合はスキップ）を実装。
    - jquants_client を経由した fetch/save の呼び出しを想定。

- リサーチ・ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率を計算。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率を計算。
    - calc_value: PER（EPS が 0/NULL の場合は None）、ROE を raw_financials と prices_daily から算出。
    - 各関数は DuckDB の SQL ウィンドウ関数を活用し、データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を LEAD を用いて取得。horizons の検証（正の整数かつ <= 252）を実装。
    - calc_ic: スピアマンランク相関（IC）計算を実装。レコード不足や分散ゼロ時は None を返す。
    - rank: 同順位は平均ランクにする実装（丸め処理で ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。

### 設計上の注意点・フェイルセーフ
- ルックアヘッドバイアス回避:
  - 各処理（AI スコアリング・レジーム判定・ファクター計算・ETL 等）は内部で datetime.today() / date.today() を直接参照せず、明示的な target_date を受け取る設計。
  - DB クエリは target_date 未満 / 間隔指定により未来データの漏えいを防止。
- 冪等性とトランザクション:
  - market_regime、ai_scores、calendar 等への DB 書き込みは冪等操作（DELETE→INSERT や ON CONFLICT を想定）とトランザクション管理（BEGIN/COMMIT/ROLLBACK）を採用。
  - ROLLBACK の失敗は警告ログで記録。
- 部分失敗耐性:
  - AI 呼び出しや外部 API に失敗しても、部分的に成功したデータを保護するための戦略（対象コードの限定 DELETE、スコア未取得ならスキップ）を実装。
  - OpenAI 呼び出しは再試行方針と非致命的フェイルバック（macro_sentiment=0.0 等）を採用。
- テスト容易性:
  - _call_openai_api などを patch してモック化可能な実装。
- 外部依存:
  - DuckDB と OpenAI SDK を前提とした実装になっている（コード内でインポートとエラー処理を行っている）。

### 既知の制約 (Known issues / Notes)
- 一部の DuckDB バインド/ executemany の挙動に依存するため、空リストでの executemany を回避するコードが含まれる（DuckDB 0.10 互換性のため）。
- news_nlp / regime_detector は OpenAI の JSON Mode （response_format）による結果を前提にしており、出力が想定外の形式だった場合はスキップする安全処理が入る。
- PBR・配当利回りなど一部バリュー指標は現バージョンでは未実装。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）

---

必要であれば、各モジュールごとの詳細な変更点（関数一覧、引数・戻り値、エラー挙動、例外ケースのログメッセージなど）を追加して詳細版の CHANGELOG を作成します。どのレベルの詳細が必要か教えてください。