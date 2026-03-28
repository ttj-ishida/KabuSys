# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

現在のバージョン: 0.1.0 (初回リリース)

---

## [0.1.0] - 2026-03-28

初期公開リリース。日本株自動売買・データ基盤のコア機能を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。パッケージバージョンは `0.1.0`。
  - public API としてモジュール群をエクスポート: data, research, ai, その他のサブモジュール群（strategy, execution, monitoring を意図した公開配列を準備）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルート検出は `.git` または `pyproject.toml` ベース）。
  - export KEY=val 形式、引用符付き値（エスケープ処理対応）、コメント処理などを扱える堅牢な .env パーサを実装。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - 設定取得用 Settings クラスを提供し、必要な環境変数の必須チェック (`_require`) とデフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を実装。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）を実装。

- データ基盤 (src/kabusys/data)
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar テーブル操作）、営業日判定ユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を実装。
    - DB 未取得時の曜日ベースのフォールバックや、冪等性・検索上限（_MAX_SEARCH_DAYS）を考慮した実装。
    - 夜間バッチ更新ジョブ calendar_update_job を追加（J-Quants API からの差分取得と保存、バックフィル・健全性チェック付き）。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを提供（ETL 実行結果、品質問題、エラー集約）。
    - 差分更新・バックフィル・品質チェックの設計に沿ったユーティリティ関数群の雛形を実装。
    - jquants_client および quality モジュールとの連携ポイントを設置（実際の API 呼び出し箇所は外部モジュール経由）。

- 研究・リサーチ (src/kabusys/research)
  - factor_research モジュール
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対ATR、平均売買代金、出来高比率）、Value（PER、ROE）などのファクター計算関数を実装（DuckDB SQL ベース）。
    - 欠損やデータ不足時の取り扱い（None返却）や、スキャン日数バッファの設計を反映。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）を汎用ホライズン対応で実装。
    - IC（Information Coefficient）計算（スピアマンの順位相関）、ランク変換ユーティリティ、ファクター統計サマリー関数を実装。
    - 外部ライブラリに依存せず標準ライブラリ＋DuckDBで動作する設計。

- AI（自然言語処理） (src/kabusys/ai)
  - news_nlp モジュール
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチセンチメント評価を実施。
    - バッチサイズ制御、最大記事数・最大文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスのバリデーションと数値クリップ (±1.0)、部分成功時の DB 書き込み保護（影響範囲を絞るDELETE→INSERT）を実装。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - regime_detector モジュール
    - ETF 1321 の 200日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - OpenAI API 呼び出し（gpt-4o-mini）を用いたマクロセンチメント算出、リトライとフォールバック（失敗時 macro_sentiment=0.0）、結果のDBへの冪等書き込みを実装。
    - ルックアヘッドバイアスを避けるため date 未満のデータのみ使用する方針を徹底。

### 変更 (Changed)
- なし（初回リリースのため該当項目なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当項目なし）。

### セキュリティ (Security)
- OpenAI API キーや各種トークンは必須環境変数として扱う実装。APIキー未設定時は ValueError を発生させて明示的に失敗させる箇所あり（news_nlp.score_news, regime_detector.score_regime 等）。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

### 既知の制約・注意点 (Notes / Known issues)
- DuckDB に依存：価格データやテーブルスキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）が前提。
- OpenAI の API 形式（JSON mode、response_format）に依存。SDK バージョン差異に配慮したエラーハンドリングを実装しているが、将来的な SDK 変更に注意が必要。
- ai.news_nlp と ai.regime_detector は意図的に内部の _call_openai_api 実装を分離している（モジュール結合を低く保つ設計）。
- 一部 DuckDB の機能やバージョン差（executemany の空リスト扱い等）に対する互換性処理を加えているが、実運用時の環境での検証を推奨。
- .env 自動読み込みはプロジェクトルートの検出に依存。配布後の利用やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による制御が可能。

---

今後の予定（例）
- 監視・実行（execution / monitoring）モジュールの実装強化とドキュメント整備
- テストカバレッジの拡張（外部 API のモックによる統合テスト）
- パフォーマンス最適化と追加ファクターの導入

--- 

（この CHANGELOG はソースコード内のドキュメント文字列・実装表現から推測して作成しています。実際のリリースノートと差分がある場合は適宜修正してください。）