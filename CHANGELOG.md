CHANGELOG
=========

すべての注目すべき変更を記録します。  
このプロジェクトは Keep a Changelog のフォーマットに準拠しています。

フォーマットの説明は省略します（初期リリースのため、主に "Added" を列挙しています）。

Unreleased
----------

- 現時点の開発中の変更（該当なし）

[0.1.0] - 2026-03-29
-------------------

初期リリース。日本株自動売買プラットフォームのコアライブラリを提供します。
主な機能は設定管理、データ ETL / カレンダー管理、リサーチ用ファクター計算、および
OpenAI を用いたニュース NLP / 市場レジーム判定です。

### Added
- パッケージメタ情報
  - kabusys パッケージのバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイル（.env, .env.local）および OS 環境変数からの設定自動読み込み機能を実装。
  - 自動読み込みの優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト等で利用）。
  - .env 解析器: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - protected パラメータによる OS 環境変数保護（.env.local の override 時に既存 OS 環境変数を上書きしない）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（必須キー未設定時は ValueError）。
  - 環境値のバリデーション: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）の検証。
  - データベースパス（DUCKDB_PATH/SQLITE_PATH）、Slack / Kabu API / J-Quants の設定をプロパティで公開。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約し、銘柄ごとのニュースを OpenAI (gpt-4o-mini) に送ってセンチメントを算出して ai_scores テーブルへ書き込み。
  - ニュース収集ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較するロジック（calc_news_window）。
  - バッチ処理: 1回の API 呼び出しで最大 20 銘柄を送信（チャンク処理）。
  - トークン肥大化対策: 1銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - OpenAI 呼び出しは JSON Mode を期待。429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ。
  - レスポンス検証: JSON パース、"results" リストの存在、各要素の code/score 型検証、未知コードは無視、スコアは ±1.0 にクリップ。
  - DuckDB 互換性考慮: executemany に空リストを渡さないガードを追加（DuckDB 0.10 対応）。
  - テスト容易性: API 呼び出し部分は _call_openai_api を patch して差し替え可能。

- AI / 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
  - マクロニュース抽出のためのキーワードリスト実装（日本・米国・グローバルの主要語）。
  - OpenAI 呼び出しのリトライ/フェイルセーフ: API 失敗時は macro_sentiment=0.0 で継続、内部で最大リトライ回数を持つ。
  - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行い、失敗時は ROLLBACK。ROLLBACK 失敗時は警告ログを出力。
  - ルックアヘッドバイアス対策: target_date 未満のデータのみを使用し、内部で datetime.today() を参照しない設計。

- Research（ファクター計算・特徴量探索） (src/kabusys/research/)
  - ファクター計算モジュール（factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー: raw_financials から EPS/ROE を組み合わせて PER/ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB のウィンドウ関数を活用した実装。
  - 特徴量探索モジュール（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンに対する将来リターンを一度に取得可能。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を独自実装（外部依存なし）。
    - ランク関数（rank）は均等ランク（同順位は平均ランク）を返す実装。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を提供。
  - 設計方針: 外部ライブラリに依存せず、DuckDB 接続で完結する設計。ルックアヘッドバイアス回避を意識。

- Data（ETL / カレンダー管理 / パイプライン） (src/kabusys/data/)
  - カレンダー管理（calendar_management.py）
    - market_calendar を基に is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB データがない場合は曜日ベースのフォールバック（土日は非営業日）。
    - next/prev_trading_day は最大探索日数制限を設けて ValueError を投げることで無限ループを回避。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を更新（バックフィル・健全性チェックあり）。
  - ETL / パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラーの集計を含む）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）の設計方針を実装。
    - jquants_client の fetch / save 関数を使用する想定（差分取得→保存→品質チェックのフロー）。
    - DuckDB テーブル存在チェック・最大日付取得ユーティリティを提供。
  - etl モジュールで ETLResult を再エクスポート。

- 互換性 / テスト向け配慮
  - OpenAI 呼び出しの箇所は内部関数を patch しやすく実装（ユニットテストでの差し替えを想定）。
  - DuckDB のバージョン差（executemany の空リスト扱い等）に配慮した実装。

### Changed
- 初回リリースのため該当なし（以降のリリースで差分を記載）。

### Fixed
- 初回リリースのため該当なし。

### Security
- 必須 API キー（OpenAI 等）は明示的に要求。環境変数未設定時は ValueError を投げることで秘密情報の欠如を検出しやすくしている。
- .env 自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テストや CI 環境での秘密漏洩リスクを低減。

Notes / 注意事項
- ルックアヘッドバイアス防止: ニュース・価格データを扱うユーティリティは内部で datetime.today() / date.today() を参照せず、ユーザーが明示的に target_date を渡す設計になっています。運用時は target_date を適切に指定してください。
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を利用する前提です。実際の API レスポンス形式やモデル名の変更に合わせて更新が必要です。
- DuckDB の SQL バインドや executemany の挙動はバージョンによって差異があり得ます。運用環境の DuckDB バージョンでの動作確認を行ってください。
- J-Quants / Kabu API 用のクライアント実装（jquants_client, kabu 関連）はモジュールの外側で提供される想定です（本コードはそれらを利用する設計）。

Authors
- 初期実装: kabusys 開発チーム（リポジトリ内コメント・設計ドキュメントに基づく実装）

ライセンス
- プロジェクトのライセンス情報はリポジトリの LICENSE を参照してください。