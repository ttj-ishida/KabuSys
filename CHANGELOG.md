# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-29

### Added
- 初回リリース。日本株自動売買用のライブラリ基盤を提供。
- パッケージメタ情報
  - `kabusys.__version__ = "0.1.0"` を追加（公開バージョン）。
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。

- 環境設定/ローダー (`src/kabusys/config.py`)
  - `.env` / `.env.local` ファイルおよび既存の OS 環境変数からの設定読み込みを実装。プロジェクトルート検出（.git / pyproject.toml）に基づき自動ロード。
  - 自動ロード抑止用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - `.env` パーサの実装（コメント行、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等をサポート）。
  - 環境変数保護: OS 環境変数を保護する `protected` セットを使い `.env.local` の上書き挙動を制御。
  - `Settings` クラスを提供し、アプリケーションに必要なキー（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティ経由で取得。env 値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。
  - DB パス（DuckDB/SQLite）を Path として解決。

- AI（NLP）関連
  - ニュースセンチメントスコアリング (`src/kabusys/ai/news_nlp.py`)
    - 前日 15:00 JST ～ 当日 08:30 JST を対象とするニュース収集ウィンドウ計算（UTC naive datetime）を実装（calc_news_window）。
    - RAW ニュースと銘柄マッピング（news_symbols）から、銘柄ごとに最新記事を集約して OpenAI にバッチ送信する処理を実装（最大バッチサイズ・トリム文字数の制御あり）。
    - OpenAI の JSON Mode を利用して厳密な JSON 応答を期待（レスポンスバリデーションを厳密に実施）。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他エラーはフェイルセーフでスキップ（例外非伝播）。
    - レスポンス検証: results リスト・コード照合・数値検証・スコアの ±1.0 クリップ。
    - 成果は ai_scores テーブルへ置換的に保存（部分失敗時に既存スコアを保護するため、対象コードを限定した DELETE→INSERT の実装）。
    - テストのために OpenAI 呼び出し箇所（_call_openai_api）を差し替え可能に設計。

  - 市場レジーム判定 (`src/kabusys/ai/regime_detector.py`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - マクロ記事抽出はキーワードベース。LLM は gpt-4o-mini を想定し JSON 出力をパース。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を実装。
    - レジーム合成ロジック、閾値（BULL/Bear）やスケーリング定数を定義。

- 研究用モジュール（Research）
  - ファクター計算 (`src/kabusys/research/factor_research.py`)
    - Momentum（1M/3M/6M リターン・MA200 乖離）、Volatility（20日 ATR）、Value（PER, ROE）などのファクター計算を実装。DuckDB SQL を用いた一貫した計算。
    - データ不足時は None を返す等、堅牢な取り扱い。
  - 特徴量探索 (`src/kabusys/research/feature_exploration.py`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク関数、ファクター統計サマリー等を実装。
    - pandas 等に依存せず標準ライブラリで実装。

- データプラットフォーム（Data）
  - カレンダー管理 (`src/kabusys/data/calendar_management.py`)
    - JPX カレンダー管理ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar 未取得時の曜日ベースのフォールバック、DB 値優先の一貫した挙動、探索上限（日数）ガードを実装。
    - J-Quants から差分取得しテーブルを更新する夜間ジョブ（calendar_update_job）を実装。バックフィルと健全性チェックあり。
  - ETL パイプライン (`src/kabusys/data/pipeline.py`, `src/kabusys/data/etl.py`)
    - 差分取得、idempotent な保存（jquants_client の save_* を利用）、品質チェック（quality モジュール）を想定した ETL の骨組みを実装。
    - ETLResult データクラスを提供し、実行結果／品質問題／エラーを集約して to_dict で整形可能。
    - DuckDB の executemany における互換性（空リスト扱い）を考慮した実装。

- 低レベルユーティリティ
  - DuckDB 結合関数や日付変換ユーティリティ、テーブル存在チェック等のヘルパを複数実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数（API キー等）を強制取得する箇所は ValueError を発生させることで、実行時に明示的にキーを要求。
- `.env.local` の読み込みは OS 環境変数を優先し、重要な既存環境変数を意図せず上書きしないよう保護。

### Notes / Implementation details / Compatibility
- すべての「日付」は timezone を含まない date / naive datetime として扱う設計（ルックアヘッドバイアス防止）。
- OpenAI API 呼び出しは JSON Mode（response_format={"type":"json_object"}）を期待するが、実運用上は余裕をもって前後テキスト混入ケース等にも対応するパースロジックを備えている。
- DuckDB に対する SQL は互換性を考慮した記述にしているが、実行環境の DuckDB バージョン差による振る舞い（list バインドなど）に注意。executemany の空リスト問題等へ対策済み。
- テスト容易性を考慮し、AI 呼び出し関数（_call_openai_api）を patch で差し替え可能にしている。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的な注文実行ロジックと安全ガードの実装。
- より細かな品質チェックルールの実装と監査ログ出力。
- CI / テストケース（DuckDB を用いた統合テスト、OpenAI 呼び出しモック）整備。

もし CHANGELOG に追記して欲しい点（例: 実装の追加/削除/日付変更など）があれば指示ください。