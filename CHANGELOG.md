# Changelog

すべての注記は Keep a Changelog のガイドラインに従っています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]
（現在未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開しました。主な追加点は以下のとおりです。

### 追加
- パッケージ公開
  - src/kabusys/__init__.py によりパッケージエントリを提供。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み順序: OS環境変数 > .env.local > .env。OS側の既存環境変数は保護（上書きされない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用）。
    - .env パーサ実装: export PREFIX=val 形式・クォートされた値とバックスラッシュエスケープ・インラインコメント処理に対応。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境 / ログレベル等の取得をプロパティ経由で行える。必須値未設定時は ValueError を送出。
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。

- AI（NLP）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode でセンチメントを計算して ai_scores に書き込む。
    - バッチ処理、1チャンク最大20銘柄（_BATCH_SIZE=20）、記事数/文字数制限によるトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しはリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。その他エラーはスキップしてフェイルセーフ。
    - レスポンスバリデーション実装（JSON 抽出、results の存在・型、コード照合、スコア数値化・有限チェック）。スコアは ±1.0 にクリップ。
    - DuckDB の executemany 空リスト制約に配慮し、書き込み前に空チェックを行う。
    - calc_news_window(target_date) により JST 時間ウィンドウ（前日15:00〜当日08:30）を UTC naive datetime として返却。ルックアヘッドバイアスを避ける設計（内部で date.today() を参照しない）。
    - score_news(conn, target_date, api_key=None) を公開。OpenAI API キー解決ロジックあり（引数優先、次に環境変数 OPENAI_API_KEY）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存する score_regime を実装。
    - マクロ記事抽出はマクロキーワードリストに基づき raw_news からタイトル抽出（最大20件）。
    - OpenAI（gpt-4o-mini）呼び出しは独立実装で、API障害時は macro_sentiment=0.0 として継続（フェイルセーフ）。リトライ・エラーハンドリングを実装。
    - レジームスコア合成とクリッピング、ラベル閾値（BULL/BEAR）による判定。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス防止の設計（prices_daily の date < target_date を用いる等）。

- リサーチ（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB による SQL/ウィンドウ関数を駆使した実装。データ不足時は None を返す設計。
    - 結果は (date, code) を含む dict のリストで返却。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns、horizons デフォルト [1,5,21]、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）を提供（calc_ic）。
    - ランク変換ユーティリティ（rank）／統計サマリー（factor_summary）を実装。
    - pandas 等の外部ライブラリに依存しない純粋 Python 実装。

  - パブリック再エクスポート
    - src/kabusys/research/__init__.py で主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

- データ基盤（Data Platform）
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB データが存在しない場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants API から差分取得し market_calendar を冪等更新。バックフィル・健全性チェック（将来日付の異常検出）を実装。
    - 探索の最大範囲制限（_MAX_SEARCH_DAYS）で無限ループを防止。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインと結果型（ETLResult データクラス）を実装。
    - 差分更新、backfill、品質チェック（quality モジュール想定）との連携、J-Quants クライアント（jquants_client）を利用した冪等保存方針を採用。
    - ETLResult は品質問題や処理エラーを収集・シリアライズ可能（to_dict）。

  - src/kabusys/data/__init__.py と etl 再エクスポートにより ETLResult を公開。

### 変更（設計注記）
- ルックアヘッドバイアス対策
  - AI スコアリング・レジーム判定・ETL 等、すべての「対象日」ロジックで date.today()/datetime.today() を直接参照しない方針を徹底。外部から target_date を注入することで検証可能性を高めています。

- OpenAI 呼び出し
  - gpt-4o-mini を想定。JSON mode を使った厳密な JSON 出力期待でプロンプトを組んでいますが、実運用での不整合に備えたパース回復処理を組み込んでいます（文字列から最外の {} を抽出する等）。
  - LLM 呼び出しのテスト容易性のため、内部の _call_openai_api をパッチ差し替え可能にしています。

- DuckDB 互換性配慮
  - executemany に空リストを渡すと失敗するバージョンがあるため、事前に空チェックを行う等の実装上の配慮を行っています。

### 修正（バグ修正 / フォールバック実装）
- エラー耐性強化
  - OpenAI API の各種例外（RateLimit, APIConnectionError, APITimeoutError, APIError）についてリトライやフォールバック（ゼロスコア）を実装し、外部 API 障害が全体処理を止めないようにしています。
  - DB 書き込みで例外が発生した場合は ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを追加。

### セキュリティ
- 必須シークレット（OpenAI API key, Slack token, Kabu API password, J-Quants refresh token 等）は Settings プロパティで明示的に必須化し、未設定時はエラーを発生させる設計としています。

---

参照:
- 各モジュールの詳細はソース内 docstring と関数ドキュメントを参照してください。追加機能・修正は Unreleased セクションに記載の上、次回リリースでバージョンを上げて反映します。