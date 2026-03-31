# CHANGELOG

すべての重要な変更はここに記録します。本ファイルは Keep a Changelog の慣習に従って作成しています。

リリース方針: バージョンは semver を想定しています。ここでは初回公開相当の 0.1.0 を記載しています。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初期リリース: kabusys - 日本株自動売買支援ライブラリの初期実装を追加。
- バージョン情報・公開 API:
  - src/kabusys/__init__.py に __version__ = "0.1.0" と公開モジュール一覧を追加（data, strategy, execution, monitoring）。
- 環境設定管理:
  - src/kabusys/config.py を追加。
  - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）を実装。
  - 読み込み優先度: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 高度な .env パーサ実装（export プレフィックス、クォート内エスケープ、インラインコメント処理等に対応）。
  - 設定アクセス用 Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の必須取得メソッド、DUCKDB/SQLITE パス、KABUSYS_ENV/LOG_LEVEL の検証ロジック）。
- AI（OpenAI）によるニュース NLP と市場レジーム判定:
  - src/kabusys/ai/news_nlp.py を実装。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄／回）、1銘柄あたり記事数と文字数制限、レスポンスバリデーションを実装。
    - 429・ネットワーク断・タイムアウト・5xx への指数バックオフリトライを実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト容易性のため _call_openai_api をパッチで差し替え可能に設計。
    - 時間ウィンドウ計算（JST 基準）を calc_news_window で提供し、ルックアヘッドバイアスを防止（内部で datetime.today() を直接参照しない）。
  - src/kabusys/ai/regime_detector.py を実装。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはマクロキーワードでフィルタ、OpenAI を用いた JSON 出力をパースしてスコア化。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックして処理継続。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
- データプラットフォーム（DuckDB ベース）:
  - src/kabusys/data/pipeline.py を実装。
    - ETL パイプラインの主要ロジック（差分取得、保存、品質チェックの骨格）を提供。
    - ETL 実行結果を表す dataclass ETLResult を定義（to_dict / has_errors / has_quality_errors を含む）。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py を実装。
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - JPX カレンダー差分取得バッチ（calendar_update_job）実装（J-Quants クライアント呼び出しを想定）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末除外）で動作する設計。
    - lookahead / backfill / 健全性チェック（将来日付異常検知）を実装。
- リサーチ（ファクター）モジュール:
  - src/kabusys/research/factor_research.py を実装。
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20 日）などのファクターを DuckDB SQL で算出する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - raw_financials と prices_daily の組合せで PER/ROE を算出。
    - 売買代金・出来高関連の流動性指標を算出。
  - src/kabusys/research/feature_exploration.py を実装。
    - 将来リターン算出（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas など外部依存を使わない純粋 Python 実装。
  - src/kabusys/research/__init__.py で主な関数群を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize の再エクスポート等）。
- ロギング・堅牢性:
  - 各モジュールで詳細な logger を使用し、重要なフェイルオーバーログを記録。
  - DB 書き込みでトランザクションと ROLLBACK を適切に扱い、ROLLBACK 失敗時に警告。
  - OpenAI 呼び出しに対する細かなエラー分類（RateLimitError, APIConnectionError, APITimeoutError, APIError）を導入し、5xx 判定や非5xx の分岐を設計。
- ドキュメント文字列（docstring）:
  - 各モジュール・関数に詳細な docstring を付与。設計方針、参照テーブル、フェイルセーフ動作、ルックアヘッドバイアス回避方針などを明記。

### 変更 (Changed)
- 該当なし（初回リリースのため）。

### 修正 (Fixed)
- 該当なし（初回リリースのため）。

### 削除 (Removed)
- 該当なし（初回リリースのため）。

### セキュリティ (Security)
- 環境変数の必須チェックを Settings クラスで行い、未設定時に明示的な ValueError を発生させることで秘密情報の欠落を早期検出。

---

備考 / 設計上の重要点（開発者向け要約）
- 外部 API（OpenAI / J-Quants 等）への依存箇所は明確に分離され、テストのために API 呼び出し関数（_call_openai_api 等）を差し替え可能にしている。
- ルックアヘッドバイアス防止: target_date ベースの処理（news/window/price クエリ）はすべて target_date 未満／前日等の排他条件を用いている。
- DB 書き込みは可能な限り冪等性を保つ（DELETE → INSERT、ON CONFLICT を想定した保存など）。
- DuckDB の executemany の挙動（空リスト渡し不可等）を考慮した実装がなされている。
- OpenAI レスポンスは JSON モードを期待するが、万が一の前後余剰テキスト混入に対する復元ロジックを実装している。

今後の予定（提案）
- strategy / execution / monitoring モジュールの具体実装（現時点ではパッケージ公開のみ）。
- より詳細なユニットテスト・統合テストの追加（API モック、DuckDB テストデータ）。
- ai モデル選択やバッチ設計のチューニング、並列化・レート制御の強化。

--- 

（この CHANGELOG はコードを解析して推測して作成しています。実際のコミット履歴やリリースノートに合わせて適宜更新してください。）