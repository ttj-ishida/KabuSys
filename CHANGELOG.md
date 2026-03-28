# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。  

リリース日付はコードベース作成時点（この CHANGELOG の作成日）を使用しています。

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買システム「KabuSys」のコアコンポーネントを一通り実装・公開。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化 `kabusys.__init__` を追加。バージョン `0.1.0`、公開 API モジュール一覧を定義。
- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの探索はこのファイル位置から行い、CWD に依存しない実装。
    - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーを実装（コメント行, export KEY=val, クォート文字列、エスケープ対応、インラインコメントの取り扱いなど）。
  - 既存の OS 環境変数を保護するための protected セットを用いた上書き制御を実装。
  - 必須設定取得用 `_require` と `Settings` クラスを提供。J-Quants / kabuAPI / Slack / DB パス / 動作環境 / ログレベル等のプロパティを公開。
  - `env` / `log_level` の検証（許容値チェック）を実装。
- AI モジュール (`kabusys.ai`)
  - ニュースセンチメント分析 (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ（JST: 前日15:00～当日08:30）計算ユーティリティ `calc_news_window` を実装（UTC naive datetime を返す）。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、銘柄ごとに記事の数/文字数制限（記事数最大10件、文字数最大3000）を導入してトークン肥大化を抑制。
    - エラー/レート制限/サーバーエラーに対する指数バックオフリトライ実装（429・ネットワーク断・タイムアウト・5xx を再試行対象）。
    - レスポンスの厳密バリデーション（JSON パース、results 配列・各要素の code/score、未知コードの無視、スコアの数値化、有限値チェック）を実装。スコアは ±1.0 にクリップ。
    - 部分失敗時に既存スコアを保護するため、取得済みコードのみ DELETE → INSERT で置換する安全な DB 書き込みロジックを採用。
    - テスト用に内部の OpenAI 呼び出し関数をパッチ差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースベースの LLM マクロセンチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定して `market_regime` テーブルへ冪等書き込み。
    - MA 計算はルックアヘッドバイアス防止のため target_date 未満データのみを使用。データ不足時は中立（ma200_ratio=1.0）にフォールバック。
    - OpenAI 呼び出しは独立実装。API 失敗時は macro_sentiment=0.0 のフェイルセーフで継続。
    - API リトライ・バックオフ、JSON パースエラー等の扱いを実装。
- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーを管理する `market_calendar` テーブル用のユーティリティを実装。
    - 営業日判定・前後営業日取得・期間内営業日一覧取得・SQ日判定等を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - カレンダーデータが未取得の場合は曜日ベース（土日除外）でフォールバックする堅牢な実装。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装し、J-Quants クライアントを使って差分取得→冪等保存を行う（バックフィル、健全性チェックあり）。
  - ETL パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL の結果を表す `ETLResult` データクラスを実装（取得数/保存数/品質問題/エラー等を保持）。
    - 差分更新、backfill、品質チェックフレームワーク（quality モジュール連携）、idempotent な保存（jquants_client の save_* 利用）等を設計に含む基礎を実装。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。
- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算群を追加。
    - `calc_momentum`: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - `calc_volatility`: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - `calc_value`: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損なら PER は None）。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - `calc_forward_returns`: 指定基準日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - `calc_ic`: ファクターと将来リターンのスピアマン（ランク相関）による IC を計算。データ不足時は None を返す。
    - `rank`: 同順位は平均ランクとするランク関数を提供（丸めによる ties 検出対策あり）。
    - `factor_summary`: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - `kabusys.research.__init__` で主要関数を公開（zscore_normalize は data.stats からの再エクスポート）。
- ロギング・DB操作の堅牢化
  - 各所で BEGIN / DELETE / INSERT / COMMIT の冪等書き込み、例外時の ROLLBACK 試行、ROLLBACK 失敗時の警告ログなどを実装。
  - 多くの処理で入力バリデーション／存在チェック（テーブル存在チェック等）を導入。

### 変更 (Changed)
- 該当なし（初期リリースのため過去リリースからの変更はなし）。

### 修正 (Fixed)
- 該当なし（初期リリース）。

### 既知の注意事項 (Notes)
- OpenAI / J-Quants への実際の API 呼び出しを行う箇所があるため、本パッケージの一部機能は API キーや外部アクセスが必要です。テスト時は内部の呼び出し関数をモック／パッチすることを想定しています。
- DuckDB のバージョン差異に対応するため、executemany に空リストを渡さない等の互換性対策を実装しています。
- 日付操作はルックアヘッドバイアス防止の観点から datetime.today()/date.today() を直接参照しない設計が各モジュールに散りばめられています（ただし calendar_update_job 等一部で実行時の today を使用）。

### セキュリティ (Security)
- OS 環境変数を自動上書きから保護する仕組み（protected set）を .env ロード処理に実装。
- API キーは引数で注入可能（テスト容易化）かつ、未指定時は環境変数 OPENAI_API_KEY を必須とすることで明確なエラーを出す設計。

---

将来的なリリースでは、テストカバレッジの追加・ドキュメント強化・監視/運用用コマンド群の追加・より細かい品質チェックの拡張を予定しています。