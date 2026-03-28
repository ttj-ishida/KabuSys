# Changelog

すべての重要な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠しています。  

- リリースの命名規則: バージョン番号 (semver)
- 日付はリリース日を示します

## [0.1.0] - 2026-03-28

初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。パッケージ外部公開用に主要サブパッケージ名を `__all__` に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索して決定（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーは以下に対応:
    - 空行・コメント行（先頭 `#`）
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のエスケープ処理（バックスラッシュ処理）
    - クォートなしの値でのインラインコメント判定（`#` の直前が空白/tab の場合をコメント扱い）
  - 読み込み時の保護動作:
    - override フラグと protected キー集合（OS 環境変数保護）をサポート。
  - 代表的な設定プロパティを提供（必須項目は未設定時に ValueError を送出）:
    - J-Quants: `jquants_refresh_token`
    - kabu: `kabu_api_password`, `kabu_api_base_url`（デフォルト付き）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`, `sqlite_path`（デフォルト付き）
    - システム設定: `env`（development/paper_trading/live のバリデーション）、`log_level`（ログレベル検証）とそれに基づく `is_live/is_paper/is_dev`。

- AI モジュール (src/kabusys/ai/)
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols からニュースを銘柄単位に集約し、OpenAI（gpt-4o-mini）に JSON モードで送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: JST 前日15:00 ～ 当日08:30（UTC に変換して DB と比較）。
    - バッチ処理: 最大 20 銘柄/リクエスト（_BATCH_SIZE）。
    - 1銘柄あたり: 最新最大 10 記事・最大 3000 文字でトリム。
    - 再試行戦略:
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（最大回数・ベースウェイト設定あり）。
      - それ以外のエラーはスキップ（フェイルセーフ）。
    - レスポンス検証:
      - 厳密な JSON 構造（"results" 配列）検証
      - unknown code の無視、数値変換と有限性チェック、±1.0 クリップ
      - JSON 前後に余計なテキストが混入した場合の最外 {} 抽出対応
    - DB 書き込み:
      - 成功取得したコードのみを対象に DELETE → INSERT の冪等更新（部分失敗時に既存スコアを保護）。
      - DuckDB の executemany の制約（空リスト不可）を考慮。
    - テスト容易性:
      - OpenAI 呼び出し部は内部関数 `_call_openai_api` として切り出し、テスト時にモック可能。
    - パブリック API: `score_news(conn, target_date, api_key=None)`（取得した銘柄数を返す）。

  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロセンチメントは `news_nlp.calc_news_window` で算出したウィンドウのマクロ関連タイトルを抽出して OpenAI（gpt-4o-mini）に渡す。
    - LLM 呼び出しは JSON モード利用、再試行・バックオフ戦略を実装し、失敗時は macro_sentiment = 0.0（フォールバック）を使用。
    - レジームスコア合成式とクリッピング、閾値（強気/弱気）に基づくラベル化を実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試行して上位へ例外を伝播。
    - テスト容易性:
      - `_call_openai_api` をモック可能にして LLM 呼び出しを差し替えられる。

  - AI パッケージエントリーポイント（src/kabusys/ai/__init__.py）に `score_news` を公開。

- Data モジュール (src/kabusys/data/)
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ロジック（market_calendar テーブル操作、営業日判定、SQ 判定、次/前営業日の取得、期間内営業日リスト取得）を提供。
    - DB にカレンダー情報がある場合は DB 値を優先、未登録日は曜日（平日）ベースでフォールバックする一貫した挙動を実装。
    - next_trading_day / prev_trading_day / get_trading_days は最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - calendar_update_job：J-Quants クライアント（jquants_client.fetch_market_calendar, .save_market_calendar を使用）から差分取得して冪等保存。バックフィルや健全性チェック（未来日付異常検出）を実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETL のインターフェースとユーティリティを実装。
    - ETLResult データクラスを導入（ターゲット日、取得数/保存数、品質チェック結果、エラー等を保持）。
    - 差分更新、バックフィル、品質チェック（quality モジュールを呼び出す）等の設計方針を実装。
    - DuckDB ヘルパー（テーブル存在確認、最大日付取得）を提供。
    - etl モジュールから ETLResult を再エクスポート。

- Research モジュール (src/kabusys/research/)
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から最新値）
    - 各関数は DuckDB を受け取り prices_daily / raw_financials テーブルのみ参照。データ不足時は None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）のリターンを一括取得。horizons のバリデーションを実施。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装（同順位に対して平均ランク処理）。
    - ランク関数（rank）: ties を平均ランクで扱う（丸め処理で浮動小数の ties 検出漏れを防止）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算（None を除外）。
  - research パッケージの __init__ で主要関数を公開（zscore_normalize は data.stats から再利用）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 注意点 / 実装上の設計判断
- ルックアヘッドバイアス対策:
  - AI モジュール・research モジュールともに内部で datetime.today()/date.today() を直接参照せず、明示的に target_date を受け取る API 設計とすることでルックアヘッドを防止。
  - DB クエリは target_date 未満・以前等の排他条件を明示している。
- フェイルセーフ:
  - LLM/API 呼び出しが失敗した場合は例外を破壊的に上げず、代替値（例: macro_sentiment=0.0）またはスキップして処理を継続する設計を採用。
- テスト容易性:
  - OpenAI 呼び出し箇所をラップしてモック差し替え可能にしている（ユニットテストでの外部 API 依存を軽減）。
- 外部依存:
  - DuckDB による内部 DB 操作を前提としている。
  - J-Quants 用クライアント（jquants_client）や quality モジュール、kabu/station や Slack 実装はこの差分で参照されるが実装ファイルは該当差分に含まれていないため、実行時に適切な実装/設定が必要。

### 既知の制約 (Known issues / future work)
- 一部モジュールは外部クライアント（jquants_client, OpenAI API）に依存するため、実行環境での API キーやネットワーク設定が必要。
- 現時点では PBR・配当利回りなどの一部バリューファクターは未実装（calc_value の注記）。
- pipeline モジュールの一部（ファイル末尾）は差分で途切れている可能性があり、引き続き補完・テストが必要。

---

今後のリリースでは、バグ修正、テスト補完、ドキュメント追加、追加ファクターや運用用監視・実行モジュール（execution / monitoring）の実装を予定しています。