# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 です。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージルート: kabusys 初期モジュール構成（data, research, ai, monitoring 相当の名前空間準備）。
  - バージョン定義: __version__ = "0.1.0" を追加。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルートの検出は __file__ から親ディレクトリを上がって .git または pyproject.toml を探す方法を採用（配布後の挙動を考慮）。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
  - 環境変数の必須チェックを行う _require 関数と Settings クラスを提供。
    - J-Quants, kabuステーション, Slack, DB パスなどの設定プロパティを実装。
    - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証を実装。
    - Path 型でのデフォルト DB パス（DuckDB / SQLite）を提供。

- データプラットフォーム機能 (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダーの取得・管理ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを追加。
    - market_calendar テーブルの有無に応じた「DB優先、未登録は曜日ベースでフォールバック」ポリシーを採用。
    - 夜間バッチ job (calendar_update_job) を実装（J-Quants クライアント経由で差分取得・保存、バックフィル・健全性チェックを含む）。
  - pipeline / etl:
    - ETL の結果を表す ETLResult データクラス（target_date / fetched/saved counts / quality_issues / errors 等）を実装し公開。
    - パイプライン用ユーティリティ（最終取得日の判定、テーブル存在チェック等）を実装。
    - 差分更新、バックフィル、品質チェックの設計方針をコードに反映（jquants_client と quality モジュールと連携想定）。
  - ETLResult は kabusys.data.etl で再エクスポート。

- ニュース NLP / LLM スコアリング (kabusys.ai)
  - news_nlp:
    - raw_news + news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出して ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）と calc_news_window を実装。
    - バッチ処理（1回あたり最大 20 銘柄）・トークン肥大化対策（記事数 / 文字数トリム）・レスポンスバリデーション（JSON 抽出、results 構造、型チェック）を実装。
    - API エラー（429/接続断/タイムアウト/5xx）は指数バックオフでリトライ。その他エラーはスキップして継続するフェイルセーフ挙動。
    - DuckDB 0.10 の制約を考慮し、executemany に空リストを渡さない安全処理を実装（部分失敗時は既存スコアを保護するため、該当コードのみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api をモジュール内で定義し、unittest.mock.patch による差し替えを想定。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を score_regime で算出・market_regime テーブルへ書き込み。
    - MA 計算は target_date 未満のデータのみを用いることでルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウからフィルタ（キーワードマッチ）し、最大 20 件を LLM に送る。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - OpenAI 呼び出しは独立実装（news_nlp と共有しない）で、同様にテスト用に差し替え可能。
    - DB 書き込みは冪等に BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を行う。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン, MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、必要な過去データのみスキャンする実装。
    - データ不足時は None を返す方針。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）を実装。範囲チェックと単一クエリ取得による最適化を行う。
    - IC（Information Coefficient）として Spearman の ρ を計算する calc_ic を実装。3 銘柄未満では None を返す。
    - ランク変換 util rank（同順位は平均ランク）および factor_summary（count/mean/std/min/max/median）を実装。
  - zscore_normalize は kabusys.data.stats から再エクスポート（research パッケージ __init__ に含む）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 特記事項なし。ただし、OpenAI API キー等の機密情報は環境変数で取り扱うことを想定。.env 読み込みはデフォルトで実行されるため、CI/本番環境では自動読み込みの有無に注意。

### 既知の制限・注意点 (Notes / Known limitations)
- 外部依存:
  - DuckDB、OpenAI SDK（OpenAI の Chat Completions を利用想定）、J-Quants クライアント（kabusys.data.jquants_client）に依存。
  - 実際の API キー（OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN 等）の設定が必須（Settings で _require するプロパティあり）。
- タイムゾーン:
  - 内部では日付/時間に timezone-aware な型を使わず、UTC naive / date オブジェクトで扱う設計（calc_news_window 等は明示的に JST→UTC に変換した naive datetime を返す）。運用時は DB 側の保存フォーマットとの整合に注意。
- ルックアヘッドバイアス対策:
  - news/price のクエリは target_date より以前のデータのみを参照する方針で実装している。ただし、呼び出し側が target_date を誤って未来日で渡すと結果は変わるため注意。
- フェイルセーフ:
  - LLM/API エラー時は例外を投げずに中立的スコアやスキップで継続する実装が多い（運用上は失敗ログを要監視）。
- DuckDB バージョン依存:
  - executemany に空リストを渡せない等の制約（DuckDB 0.10 を想定）を考慮したガード処理を実装。
- テスト支援:
  - news_nlp, regime_detector 共に内部の _call_openai_api を差し替えられるように実装しており、ユニットテストで外部 API をモック可能。

### マイグレーション / 準備 (Migration / Setup)
- 必須環境変数（例）
  - OPENAI_API_KEY（news_nlp / regime_detector）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 連携）
  - KABU_API_PASSWORD（kabu ステーション連携）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知機能が有る場合）
- オプション / デフォルト
  - DUCKDB_PATH / SQLITE_PATH（デフォルト: data/kabusys.duckdb, data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG / INFO / ...、デフォルト INFO）
- 自動 .env 読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

今後の変更はこのファイルに記録してください。