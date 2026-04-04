CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)。
- 基本モジュール構成を追加:
  - kabusys.config
    - .env / .env.local をプロジェクトルート (.git または pyproject.toml を探索) から自動読み込みする仕組みを実装。
    - export 形式やクォート文字、行内コメントの扱いに対応した .env パーサを実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視 /システム設定等の環境変数をプロパティ経由で取得。必須値の未設定時は明示的に ValueError を送出。
    - OS 環境変数の上書きを防ぐための protected キー集合を利用した .env 上書きロジックを実装。

- AI（自然言語処理）モジュール:
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI (gpt-4o-mini、JSON mode) にバッチ送信しセンチメントを算出。
    - チャンク処理 (_BATCH_SIZE=20)、記事数・文字数上限、API リトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
    - レスポンスの頑健なバリデーション（JSON パース、results リスト、code/score の型チェック、score の ±1.0 クリップ）を実装。
    - DuckDB への書込みは部分更新（該当コードのみ DELETE → INSERT）で部分失敗時の既存データ保護を実施。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（unittest.mock.patch を想定）。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離 (重み70%) とマクロ経済ニュースの LLM センチメント (重み30%) を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算、マクロ記事はマクロキーワードで抽出して LLM に渡す。LLM は gpt-4o-mini を使用。
    - API エラー時は安全に macro_sentiment=0.0 にフォールバックし処理継続。
    - market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB 書込み失敗時は ROLLBACK を試行して例外を上位へ送出。

- データ（Data Platform）モジュール:
  - kabusys.data.calendar_management
    - JPX カレンダー管理: market_calendar を基に営業日判定、翌営業日/前営業日/期間内営業日取得、SQ日判定などのユーティリティを提供。
    - DB にカレンダーがない場合は曜日ベース（平日）でフォールバックする一貫した動作設計。
    - calendar_update_job: J-Quants API から差分取得し冪等保存。バックフィルや健全性チェックを実装。

  - kabusys.data.pipeline / kabusys.data.etl
    - ETL パイプラインの骨子を実装。差分取得、保存（jquants_client 経由で冪等保存）、品質チェック呼び出しのフローを定義。
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー一覧などを含む）。has_errors / has_quality_errors 等のユーティリティを提供。
    - DuckDB の互換性を考慮した実装（executemany に空リストを渡さない等の注意点を反映）。

- リサーチ（ファクター計算／特徴量探索）モジュール:
  - kabusys.research.factor_research
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER / ROE）などのファクター計算関数を実装。
    - DuckDB を用いた SQL ベースの実装。データ不足時は None を返す仕様。
  - kabusys.research.feature_exploration
    - 将来リターン計算 (calc_forward_returns)、IC（Spearman ρ）計算 (calc_ic)、ランク変換 (rank)、統計サマリー (factor_summary) を実装。
    - pandas 等外部依存を使わずに標準ライブラリで実装。

- その他
  - モジュール間の結合を抑えるため、各モジュールで OpenAI 呼び出し用の内部関数を独立実装（テストで差し替え可能）。
  - 各所で "ルックアヘッドバイアス防止" ポリシーを適用し、date.today()/datetime.today() を直接利用しない設計。

Security
- 環境変数の読み込みにおいて既存の OS 環境変数は保護され、.env による上書きはデフォルトで行わない。必要に応じて .env.local で上書きを許可する。
- API キーが未設定の場合は明示的に ValueError を送出することで誤った無効キー利用を防止。

Fixed
- （初回リリースのため特記事項なし）

Changed
- （初回リリースのため特記事項なし）

Removed
- （なし）

Deprecated
- （なし）

Notes / Known issues
- OpenAI API（gpt-4o-mini）を利用するため、環境変数 OPENAI_API_KEY の設定が必須。未設定時は score_news / score_regime が ValueError を送出する。
- LLM レスポンスのパース失敗や API 障害は設計上フェイルセーフ（スコア 0.0 を採用、または該当銘柄/チャンクをスキップ）としているため、外部要因で一部スコアが欠落する可能性がある。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装を行っているが、運用環境の DuckDB バージョンによる挙動差は注意が必要。
- calendar_update_job 等で J-Quants クライアント（jquants_client）に依存しているため、J-Quants API の仕様変更や認証の影響を受ける可能性がある。
- 本リリースは "アルゴリズム評価 / データ処理" を主目的としており、発注（実売買）ロジックは本コードベースに含まれていない、あるいは本番への接続は明示的に区別される設計（KABUSYS_ENV で live/paper_trading/development を切替）になっている。

Contributing
- バグ報告・改善提案は issue を立ててください。設計方針（ルックアヘッド回避、DB 冪等性、フェイルセーフ設計）を維持する形での PR を歓迎します。