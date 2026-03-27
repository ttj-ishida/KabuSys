# CHANGELOG

すべての重要な変更を時系列で記録します。本ファイルは Keep a Changelog の形式に準拠しています。

注意: この CHANGELOG は提供されたコードベースの内容（コメント・実装）から推測して作成しています。実際のコミット履歴ではない点にご留意ください。

## [Unreleased]
- 今後の予定（例）
  - テストカバレッジの拡充（DuckDB モックや OpenAI 呼び出しのモック）
  - 一部未実装の研究指標（PBR・配当利回り等）の追加
  - エンドツーエンドの監視・アラート機能の強化

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買プラットフォームの基本コンポーネントを実装。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン `0.1.0` を設定（src/kabusys/__init__.py）。
  - パブリックモジュールとして data, strategy, execution, monitoring を公開。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート探索機能を .git または pyproject.toml 基準で実装し、CWD に依存しないロードを実現。
  - .env パーサを独自実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - .env ロード順序: OS 環境 > .env.local > .env（.env.local は上書き許可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを提供し、必要な環境変数取得（J-Quants、kabuステーション、Slack 等）とバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - データベースパス用プロパティ（duckdb, sqlite）を Path 型で返す。

- AI サブシステム（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30 JST）を calc_news_window として提供。
    - バッチサイズ、記事数・文字数上限、JSON モード応答検証、スコアクリップ（±1.0）を実装。
    - API の429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造、コード検証、数値検査）。
    - DuckDB への書き込みは冪等操作（対象コードのみ DELETE → INSERT）で部分失敗時の保護を実施。
    - API キー注入（引数）または環境変数 OPENAI_API_KEY をサポート。未設定時は ValueError を送出。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を用いたデータ取得、ルックアヘッドバイアス防止（target_date 未満のみ使用）。
    - マクロキーワードでニュースをフィルタして LLM (gpt-4o-mini) により JSON で macro_sentiment を取得。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出しのリトライ制御（最大試行回数、指数バックオフ）、レスポンスパース失敗の安全なハンドリング。

- 研究（research）パッケージ（src/kabusys/research）
  - factor_research: ファクター計算（momentum, value, volatility）を実装
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離 (ma200_dev)
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
    - Value: PER（EPS に依存）および ROE（raw_financials から取得）
    - 入出力は (date, code) をキーとする dict のリスト。データ不足時は None を返す方針。
  - feature_exploration: 将来リターン・IC・統計サマリー
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算。horizons の検証あり。
    - calc_ic: スピアマン（ランク）相関で IC を計算（有効レコード数が3未満なら None）。
    - rank: 同順位は平均ランクで処理するランク関数（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。

- データプラットフォーム（data）コンポーネント
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ヘルパー（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータが無い場合は曜日（平日/週末）ベースのフォールバックを使用。
    - calendar_update_job により J-Quants API からの差分取得と冪等保存をサポート（バッファ・バックフィル・健全性チェック実装）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を実装し ETL 実行結果の集約（取得・保存数、品質問題、エラーリスト）を提供。
    - 差分更新ロジック、最終取得日の算出ユーティリティ、テーブル存在チェック等を実装。
    - jquants_client との統合ポイントを設け、品質チェックモジュールと組み合わせる設計。
  - etl モジュールでは pipeline.ETLResult を再エクスポート。

- その他
  - DuckDB を主要なローカル解析 DB として利用する設計を反映（各モジュールで DuckDB 接続を受けるインターフェース）。
  - OpenAI SDK（OpenAI クライアント）を使用。API 呼び出し箇所はテスト容易性のため差し替え可能に実装（内部 _call_openai_api を patch 可能）。

### 変更・設計上の注意（ドキュメント的記述）
- ルックアヘッドバイアス対策:
  - ほとんどのモジュールで datetime.today()/date.today() を直接参照せず、target_date を明示的引数として受ける設計。
  - DB クエリは target_date 未満（排他）や LEAD/LAG の正しいウィンドウ指定などで将来データの参照を避ける実装を採用。

- フェイルセーフ設計:
  - AI API の失敗時は例外を上位に投げず、デフォルト値（例: macro_sentiment=0.0）やスキップで継続する方針が取られている。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）と冪等操作で安全性を確保。

- DuckDB 互換性配慮:
  - executemany に空リストを渡さないチェック、list バインドの回避（個別 DELETE 実行）など、DuckDB バージョン差分に配慮した実装。

### 既知の制限 / 未実装事項
- 一部のファクター（PBR・配当利回り）は未実装（コメントに明記）。
- strategy / execution / monitoring 等のモジュールファイル本体はこのスナップショットに含まれていないため、発注ロジック・実運用モニタリング等の実装状況は不明。
- OpenAI のモデル名として gpt-4o-mini を使用しているが、将来的なモデル更新や SDK 変更に対して互換性検討が必要。
- テスト記述は含まれていないため、ユニットテスト・統合テストの整備が今後の課題。

---

参考:
- 本 CHANGELOG はコード中のコメントと実装から再構築したものであり、実際のリリースノートやコミットログとは異なる可能性があります。必要であれば、コミット履歴やリリース日・変更差分を基に日付や項目を正確化します。