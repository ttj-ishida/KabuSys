CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース: kabusys パッケージの基本機能群を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py: バージョン __version__ = "0.1.0"、公開モジュール一覧を定義（data, research, ai などへのエントリポイント）。
  - 設定・環境変数管理
    - src/kabusys/config.py:
      - .env ファイルおよび環境変数の読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
      - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
      - export KEY=val 形式やシングル/ダブルクォート、行内コメントのパースに対応する堅牢な _parse_env_line 実装。
      - override / protected を考慮した .env 上書きロジック。
      - Settings クラスによりアプリ設定を公開（J-Quants, kabu API, Slack, DB パス, 環境種別/ログレベル検証等）。
  - AI（ニュース NLP / レジーム判定）
    - src/kabusys/ai/news_nlp.py:
      - raw_news / news_symbols を集約して銘柄単位のニュースを OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへスコアを書き込む処理を実装。
      - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST）、1銘柄あたりの最大記事数・文字数制限、バッチサイズ、JSON Mode を用いた厳格なレスポンスバリデーションを実装。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、失敗時はスキップ継続（フェイルセーフ）。
      - DuckDB executemany の空リスト問題を回避する保護ロジック（空時は実行しない）。
      - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定するロジックを実装。
      - マクロキーワードによる記事抽出、OpenAI 呼び出しのリトライ戦略、API 失敗時のフォールバック（macro_sentiment=0.0）。
      - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。
      - lookahead バイアス防止のため datetime.today() を参照せず target_date ベースで計算。
  - データプラットフォーム（ETL / カレンダー管理）
    - src/kabusys/data/pipeline.py:
      - ETL パイプラインの基礎実装と ETLResult データクラスを提供（取得件数、保存件数、品質チェック結果、エラー一覧を保持）。
      - 差分取得、バックフィル、品質チェック方針を想定した設計。
      - DuckDB 用のユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
    - src/kabusys/data/etl.py:
      - pipeline.ETLResult を再エクスポート。
    - src/kabusys/data/calendar_management.py:
      - JPX カレンダーの管理（market_calendar）と営業日判定ユーティリティを提供:
        - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - market_calendar が未取得時の曜日ベースフォールバック、DB 登録値優先の一貫した挙動。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル、健全性チェックあり）。
    - src/kabusys/data/__init__.py: データパッケージ初期化（jquants_client などの参照を想定）。
  - Research（ファクター計算 / 特徴量探索）
    - src/kabusys/research/factor_research.py:
      - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）などのファクター算出を実装。DuckDB 上の SQL とウィンドウ関数を活用。
      - データ不足時の None 返却、ログ出力、計算対象の明確化。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman ランク相関）calc_ic、rank、factor_summary（count/mean/std/min/max/median）を実装。
      - 外部依存を避ける標準ライブラリのみの実装方針。
    - src/kabusys/research/__init__.py:
      - 主要関数を公開（calc_momentum / calc_value / calc_volatility / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。
  - その他
    - API 呼び出し箇所（OpenAI）はテストで差し替え可能に設計（unittest.mock.patch 等を想定）。
    - ロギングと警告の充実（パースエラー、APIエラー、データ不足等での警告出力）。
    - 多くの箇所で入力検証と明示的な例外（ValueError）を用意（環境変数未設定、無効な引数等）。

Notes / 設計上の注意点
- ルックアヘッドバイアス回避: AI モジュールや ETL/Research 関数は内部で datetime.today() を参照せず、必ず外部から渡される target_date を基準に動作します。
- OpenAI API 周り:
  - JSON Mode（response_format による JSON オブジェクト期待）で厳密な JSON を期待する一方、実際のレスポンスに余計なテキストが混ざる場合を考慮して安全にパース・復元する処理を備えています。
  - リトライ対象（RateLimit, 接続エラー, タイムアウト, 5xx）と非リトライ対象を区別しており、フェイルセーフの挙動（0.0 やスキップ）を採用しています。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗する点を考慮し、空時はスキップする実装としています。
- 環境変数の自動読み込み:
  - プロジェクトルート検出によりワークディレクトリに依存せず .env を自動読み込みしますが、テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます。
- DB 書き込み:
  - 多くの書き込み処理は冪等性を意識（DELETE→INSERT、ON CONFLICT など）し、例外時にはロールバックを試みます。ロールバック失敗は警告ログで通知します。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Acknowledgements
- OpenAI API, J-Quants API, DuckDB を想定した実装と設計方針に基づく初期機能群。