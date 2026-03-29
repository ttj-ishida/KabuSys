CHANGELOG
=========
（このプロジェクトは Keep a Changelog の形式に準拠しています。すべての注目すべき変更をここに記載します。）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - src/kabusys/__init__.py にパッケージメタ情報（__version__, __all__）を追加。

- 設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能に（J-Quants トークン、kabu API、Slack、DB パス、環境/ログレベル等）。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live / is_paper / is_dev のユーティリティ。

- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - ニュースの銘柄別センチメント解析機能を実装（score_news）。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST の記事を対象（UTC 変換で DB クエリ）。
    - 銘柄ごとに最新記事を集約し、1チャンク最大20銘柄で OpenAI（gpt-4o-mini）へバッチ送信。
    - レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、結果を ai_scores テーブルへ冪等的に保存（DELETE→INSERT の実装）。
    - リトライ / バックオフ戦略（429・ネットワーク断・タイムアウト・5xx を対象）とフォールバック（API 失敗時は該当チャンクをスキップして継続）。
    - JSON mode のレスポンスノイズ（前後の余計なテキスト）に対する復元ロジックを実装。

  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定（score_regime）を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して 'bull' / 'neutral' / 'bear' を判定。
    - マクロニュース抽出（キーワードベース）→ OpenAI 判定 → スコア合成 → market_regime テーブルへ冪等書き込み。
    - API 呼び出しに対するリトライ / バックオフ、API エラーやパース失敗時のフォールバック（macro_sentiment = 0.0）。

  - 共通設計
    - OpenAI 呼び出しは各モジュール内で独立実装（モジュール結合を避ける）。
    - テスト容易性のため内部の API 呼び出し関数を patch できるように設計。

- データ管理（Data Platform）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar がない／未登録日の場合は曜日ベースのフォールバック（週末=休場）。
    - calendar_update_job: J-Quants から差分取得 → 冪等保存、バックフィル、健全性チェック実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基盤実装。
    - 差分取得、保存（jquants_client 経由で idempotent 保存）、品質チェックのフレームワーク。
    - ETLResult dataclass を提供（取得件数、保存件数、品質問題、エラー一覧などを格納）。
    - DuckDB での最大日付取得、テーブル存在チェック等ユーティリティ実装。
    - ETL 実行結果を辞書化する to_dict を実装（品質問題のタプル化）。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

  - src/kabusys/data/__init__.py
    - データパッケージ準備（将来的な公開 API 収束点）。

- リサーチ／ファクター群
  - src/kabusys/research/factor_research.py
    - momentum, volatility, value などの定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離計算（データ不足時の None 処理）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
      - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（最新報告日以前のレコードを使用）。
    - DuckDB のウィンドウ関数を多用した SQL ベース実装でパフォーマンスを重視。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク関数、統計サマリー（factor_summary）を実装。
    - 外部依存無しで純粋 Python + DuckDB SQL による実装。
    - rank は同値（ties）を平均ランクで処理し、丸め誤差対策を実施。

Changed
- （初回リリースのため過去の変更はなし）

Fixed
- （初回リリースのため過去の修正はなし）

Security
- （初回リリースのため特記事項なし）

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策:
  - ニュース・レジーム・ファクター計算関数はいずれも datetime.today() / date.today() を内部で参照せず、target_date を明示的に受け取る設計。
  - DB クエリは target_date を境に排他条件（date < target_date など）を採用して将来情報を参照しないようにしている。
- DB 書き込みの冪等性:
  - market_regime / ai_scores などへの書き込みは DELETE → INSERT（トランザクション）や executemany を用いることで冪等性を確保。
  - DuckDB の executemany の制約（空リスト不可）に対するガードを実装。
- OpenAI 統合:
  - gpt-4o-mini（JSON mode）を利用。レスポンスのパース失敗や API エラーはフォールバック（0.0 等）で許容し、例外で処理全体を止めない方針。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他の API エラーは非リトライでスキップ。
- ローカル環境の利便性:
  - .env と .env.local の読み込み順序・上書き規則を定義（OS 環境変数を保護する protected セットを利用）。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を設定して簡単にローカル実行可能。
- テスト容易性:
  - OpenAI 呼び出し箇所をモック差し替え可能に設計（内部の _call_openai_api を patch することで API 呼び出しを模擬可能）。

Breaking Changes
- なし（初回リリース）

今後の予定（予定事項）
- モニタリング / 実行（execution, monitoring）モジュールの実装拡充と公開 API の整備。
- J-Quants クライアント周り（jquants_client）の拡張と品質チェックの強化。
- 単体テスト・統合テストの追加（特に OpenAI 呼び出しと DB 書き込み周辺）。

Contributing
- バグ報告や改善提案は Issue を作成してください。パッチは PR で歓迎します。

ライセンス
- ソースツリーに含まれるライセンスに従ってください。