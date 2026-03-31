CHANGELOG
=========

すべての注目すべき変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Unreleased — 次リリースに向けた未リリースの変更（空の場合はなし）
- 各リリースは日付付きで記載し、Added / Changed / Fixed / Security 等のカテゴリで整理します。

Unreleased
----------
- （現在未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - Python パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサは複数のケースに対応:
    - export KEY=val 形式
    - シングル/ダブルクォートやバックスラッシュエスケープの扱い
    - コメント行やインラインコメントの処理（クォート内は無視）
  - Settings クラスを提供し、アプリケーションで使用する設定値をプロパティとして公開:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境（development/paper_trading/live）など。
  - 必須値未設定時は ValueError を投げる _require ユーティリティを実装。
  - LOG_LEVEL / KABUSYS_ENV の値検証を追加。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事・文字数の上限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - JSON Mode を利用した厳密なレスポンス検証と復元処理（前後ノイズが混入した場合の最外 {} 抽出）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。許容失敗時はスキップして継続するフェイルセーフ設計。
    - DuckDB executemany の空リスト制約に対する保護（空時は executemany を呼ばない）。
    - 出力を ±1.0 にクリップして保存。
    - エントリポイント: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）の合成で市場レジーム（bull/neutral/bear）を日次判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出のためのキーワードリストと、OpenAI による JSON レスポンスパースを実装。
    - API 呼び出し/パース失敗時は macro_sentiment=0.0 にフォールバック（警告ログ）。
    - OpenAI 呼び出しはモジュール内で独立実装（テスト容易化のため差し替え可能）。
    - エラー時はトランザクションをロールバックして上位へ伝播。

- リサーチ（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の取り扱い（必要行数未満は None を返す）やスキャンバッファを明示。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman ランク相関）、rank、factor_summary（統計サマリー）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージは必要なユーティリティを再エクスポート。

- データプラットフォーム（src/kabusys/data）
  - calendar_management.py
    - market_calendar を用いた営業日判定ユーティリティ群を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にデータがない場合は曜日ベース（土日を非営業日）でフォールバック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存の実装（jquants_client 呼び出し）。
  - pipeline.py / etl.py
    - ETLResult dataclass を提供し（target_date, fetched/saved counts, quality_issues, errors 等）、結果の辞書化ユーティリティを実装。
    - ETL パイプライン設計（差分更新・backfill・品質チェック方針）を文書化。
    - jquants_client と quality モジュールを利用する想定。

- テスト性 / 実運用を意識した実装
  - OpenAI 呼び出し箇所は内部関数（_call_openai_api）で一括管理しており、unittest.mock.patch による差し替えが容易。
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() をスコア計算内部で直接参照しない設計指針を採用（target_date 引数で制御）。
  - ロギングを広く利用し、異常時に詳細情報を残す設計。

Fixed
- API 呼び出し / JSON パース失敗時の堅牢性を強化（例: news_nlp, regime_detector でのフォールバック処理、警告ログ出力）。
- DuckDB executemany の空リスト問題に対処（空時は呼ばないようガード）。

Security
- 環境変数依存の機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）を Settings 経由で必須チェックする実装を追加。未設定時は明示的な ValueError を発生させる。
- .env 自動読み込みは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Known issues / Notes
- 本バージョンは OpenAI SDK（OpenAI client）と DuckDB に依存します。実行環境に応じたバージョン互換性に注意してください。
- news_nlp/regime_detector は gpt-4o-mini を想定したプロンプト設計・JSON Mode を使用しています。モデルやレスポンス仕様の変更がある場合はバリデーションロジックの調整が必要です。
- DuckDB のバージョンによってはリスト型バインドや executemany の挙動が異なるため、該当処理は互換性確保のために個別 DELETE / INSERT を行っています。
- calendar_update_job は jquants_client の実装に依存します。API 側の仕様変更は影響を与えます。

Acknowledgements
- このリリースはデータ取得（J-Quants 想定）、市場データ処理（DuckDB 想定）、および OpenAI を用いた NLP/センチメント評価のプロトタイピング基盤を提供します。

-----

今後の予定（例）
- モニタリング・実行コンポーネント（execution / monitoring）の公開インターフェース実装
- テストカバレッジの拡充（unit / integration）
- モデル切替や費用対策のためのバッチ最適化（OpenAI 呼び出しのキュー・キャッシュ）
- ai_scores / market_regime の履歴解析・可視化ユーティリティ追加

（以上）