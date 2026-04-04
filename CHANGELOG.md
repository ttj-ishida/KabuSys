# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-04
初回リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。パッケージのバージョンは `0.1.0` に設定。
  - パッケージ公開インターフェースとして `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定 & 自動.env ロード
  - 環境変数・設定管理モジュール `kabusys.config.Settings` を追加。
    - 必須環境変数取得時に未設定なら `ValueError` を送出する `_require` を提供。
    - J-Quants / kabuステーション / LINE / DB / 監視 / ログレベル等の設定プロパティを実装。
    - `KABUSYS_ENV` と `LOG_LEVEL` の検証（許可値チェック）を実装。
    - `duckdb` / `sqlite` 用のデフォルトパスや監視用フラグなど多数の設定を提供。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を起点）。
  - .env ファイル自動ロード機能を実装（優先順位: OS 環境 > .env.local > .env）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - `.env` のパースはクォート・エスケープ・コメント（スペース直前の `#`）に対応。
    - OS 環境変数を保護する `protected` 処理を実装（上書きを防止）。

- データプラットフォーム （kabusys.data）
  - カレンダー管理モジュール `calendar_management` を実装。
    - JPX カレンダー（market_calendar）を用いた営業日判定・前後営業日取得・期間内営業日列挙・SQ判定などを提供。
    - DB にカレンダーが存在しない場合は曜日ベースでフォールバック。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants クライアント呼び出し、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン基盤 `pipeline` を実装。
    - 差分取得・バックフィル・品質チェック連携の設計。
    - ETL 実行結果格納用データクラス `ETLResult` を公開 (`kabusys.data.etl` 経由で再エクスポート)。
    - DuckDB 周りの互換性考慮（executemany に空リストを渡さない等）の注意を反映。

- 研究（Research）機能（kabusys.research）
  - ファクター計算モジュール `factor_research` を追加。
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR、ATR割合）、Value（PER、ROE）等を計算。
    - DuckDB を用いた SQL ベース実装、結果は (date, code) ベースの辞書リストで返却。
  - 特徴量探索モジュール `feature_exploration` を追加。
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク変換、ファクター統計サマリを実装。
    - 外部依存（pandas 等）を使わない純 Python 実装を採用。
  - `zscore_normalize`（data.stats から）を再エクスポートし、研究 API を統合。

- AI / ニュース解析（kabusys.ai）
  - ニュース NLP スコアリング `news_nlp.score_news` を実装。
    - 指定ニュースウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算、raw_news と news_symbols を結合して銘柄ごとに記事を集約。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチセンチメント解析。1回の呼び出しで最大 20 銘柄を処理。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフ再試行を実装。
    - レスポンスバリデーション（JSON 抽出、results 配列、code 照合、スコア数値性チェック）を実装。
    - スコアを ±1.0 にクリップし、取得済みコードのみを DELETE → INSERT で冪等に更新（部分失敗時のデータ保護）。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api の patch）。
  - 市場レジーム判定 `ai.regime_detector.score_regime` を実装。
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' 判定。
    - マクロ記事取得にマクロキーワードフィルタを実施。LLM 呼び出し失敗時は macro_sentiment=0.0 でフォールバック。
    - 冪等な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI API エラー時のリトライ・5xx の扱いなど堅牢な実装。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 注意点 / 設計上の決定
- ルックアヘッドバイアス回避:
  - すべてのモジュールで内部的に `datetime.today()` / `date.today()` を参照しない設計。呼び出し元から `target_date` を渡す方式を徹底。
  - DB クエリは厳密に `< target_date` / `date = ?` 等を使いルックアヘッドを防止。
- フェイルセーフ:
  - AI API 呼び出しが失敗しても例外で全処理を止めず、該当部分は「中立（0.0）」やスキップで継続する実装が多い（運用上の安全優先）。
- OpenAI 依存:
  - `gpt-4o-mini` を想定した JSON Mode 経由での呼び出しを使用。呼び出し失敗やパース失敗のフォールバックを多数実装。
  - テスト容易性のため、内部の API 呼び出し関数をモックしやすく設計（関数分離）。
- DuckDB 互換性:
  - DuckDB の挙動（executemany に空リストを渡せない等）を考慮した実装。
  - DB 書き込みは基本的に冪等（DELETE → INSERT や ON CONFLICT 想定）で設計。
- .env パーサー:
  - 引用符・エスケープや export プレフィックス、インラインコメントの扱いを細かく実装。
  - OS 環境変数はデフォルトで保護され、.env による上書きは明示制御（.env.local は上書き可）する方針。
- ロギングと検証:
  - 設定値のバリデーション（環境名、ログレベル等）、各処理に詳細なログ（INFO/WARNING/DEBUG）を仕込んでいる。

### 既知の制約 / 今後の改善候補
- news_nlp / regime_detector ともに OpenAI の JSON Mode に依存しているため、モデルや SDK の将来的な仕様変更に備えた追従が必要。
- ai スコアやレジーム判定の閾値・重みは定数で定義されている（将来的に設定化を検討）。
- ETL パイプラインや calendar_update_job の細かな挙動は外部 J-Quants クライアントの振る舞いに依存するため、外部 API の変更時に追加対応が発生し得る。
- 現状テスト用フックは用意されているが、エンドツーエンドの統合テストやモック実装の充実化が望ましい。

---

（本CHANGELOGはソースコードの実装内容とドキュメント文字列から推測して作成しています。実際のリリースノートとして用いる場合は、リリース時の差分・コミット履歴に基づいて調整してください。）