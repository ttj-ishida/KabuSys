CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
慣例に従い、セマンティックバージョニングを使用しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

Unreleased
----------
（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-02
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開インターフェースを定義（src/kabusys/__init__.py）。主要サブパッケージとして data, strategy, execution, monitoring を想定してエクスポート（将来的な機能拡張を想定したレイアウト）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行う（CWD 非依存）。
  - .env のパースは以下に対応:
    - コメント行、export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどの堅牢なパーサ実装。
  - 必須設定取得用の _require、Settings クラスを提供。J-Quants / kabu ステーション / Slack / DBパス /監視閾値など主要設定をプロパティで提供。
  - 環境変数値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して、銘柄ごとに OpenAI (gpt-4o-mini) に送信しセンチメント (ai_score) を計算・ai_scores テーブルへ保存。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/呼び出し）、1銘柄あたりの最大記事数・文字数トリム (_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK) を実装。
    - JSON Mode を利用した厳密なレスポンス検証、レスポンスの復元・パースロバスト化（前後テキストが混入したケースの復元等）。
    - リトライ/バックオフロジック: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。非再試行エラーはスキップして安全に継続するフェイルセーフ設計。
    - スコアは ±1.0 にクリップ。部分失敗時にも既存データを保護するため、書き込み前に対象 code を限定して DELETE → INSERT の冪等処理を行う。
    - テスト容易性のため OpenAI 呼び出しラッパー（_call_openai_api）に差し替えポイントを用意。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - ニュース選定はマクロキーワードによるタイトルフィルタ（MAX 件数制限）。
    - LLM 呼出しは gpt-4o-mini + JSON Mode、API エラー時には macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - レジーム合成のクリップ・閾値（BULL/BEAR）と冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - Look-ahead バイアス対策として datetime.today()/date.today() を参照しない設計（target_date を明示的に受け取る）。
- Data プラットフォーム / ETL (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない箇所は曜日ベース（土日）でフォールバックする堅牢設計。
    - calendar_update_job により J-Quants API からの差分フェッチと冪等保存（fetch → save）を実装。バックフィルや健全性チェックを備える。
  - ETL パイプラインインターフェース (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを定義し、取得件数・保存件数・品質問題（quality モジュール由来）・エラー集約を行う。
    - 差分更新・バックフィル・品質チェックなど ETL の設計方針を反映（J-Quants クライアント経由での安全な保存、部分失敗時の保護）。
- Research（因子・特徴量探索） (src/kabusys/research)
  - factor_research モジュール (src/kabusys/research/factor_research.py)
    - Momentum (1M/3M/6M)、200 日移動平均乖離、ATR（20 日）、出来高・売買代金に基づく流動性指標などを DuckDB の SQL と Python で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 欠損データに対する扱い（必要行数未満は None とする）を明確に実装。
  - feature_exploration モジュール (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで動作する実装。
  - research パッケージのエクスポートを調整（zscore_normalize を data.stats から再利用）。
- 実運用配慮・設計上の決定
  - ルックアヘッドバイアス防止: 多くの分析・AI スコアリング関数は target_date を明示的に受け取り、datetime.today()/date.today() の使用を避ける設計。
  - DuckDB を一次データベースとして前提（関数は DuckDB 接続を受け取り SQL を活用）。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 相当の扱い）して部分失敗が全体性を損なわないよう配慮。
  - OpenAI 呼び出しは JSON Mode を使い、レスポンス検証とリトライ/バックオフを実装して堅牢化。
  - テストしやすさを考慮し、外部呼び出しポイント（_call_openai_api 等）を差し替え可能に実装。
- ドキュメント / コードコメント
  - 各モジュールに処理フロー、設計方針、例外ハンドリング方針、注意点（DuckDB の executemany の空リスト制約など）を詳細に注釈として記載。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Deprecated
- 初版リリースのため該当なし。

Security
- 環境変数による機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN など）の必須チェックを実装。自動ロード時も OS の既存環境変数を protected として上書きを防止。

Known issues / Notes
- strategy / execution / monitoring パッケージはパッケージ列挙上に含まれるが（__all__）、今回提供コードスニペットにそれらの具体実装は含まれていません。今後のリリースで注文実行や監視機能を実装予定です。
- OpenAI のモデル名や API 形式は将来の SDK 変更で互換性に影響する可能性があるため、API 呼び出し周りは注意して保守する必要があります。
- DuckDB のバージョン差異により一部バインド（list → ANY など）が不安定になるため、現実装では互換性の高い executemany ベースの削除/挿入戦略を採用しています。

今後の予定（参考）
- 注文発注（execution）と実行監視（monitoring）の実装
- strategy の戦略評価およびバックテスト機能の追加
- ai モジュールのモデル選択・プロンプト最適化・キャッシュ機構の導入
- ETL の並列処理と詳細な品質チェック強化

--- 

（この CHANGELOG は現行のコードベースからの仕様・実装をもとに推測して作成しています。実際のリリース履歴やリリース日付はプロジェクトの運用に合わせて調整してください。）