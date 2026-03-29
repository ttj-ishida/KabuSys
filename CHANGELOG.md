CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
安定版リリース: 0.1.0

Unreleased
----------

（現時点のコードベースは初期リリース相当のため、Unreleased セクションは空です。）

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - パブリック API: data, strategy, execution, monitoring のサブパッケージを公開。

- 環境設定/読み込み機能
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
    - 自動 .env ロード（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。.env.local は .env を上書き。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、行末コメント処理に対応。
    - 必須環境変数未設定時は明示的なエラー（ValueError）を返すヘルパーを提供。
    - env 値・log level のバリデーション（許容値チェック）と便利プロパティ（is_live/is_paper/is_dev）を提供。
    - デフォルト値: KABUSYS_ENV=development, KABUS_API_BASE_URL 等。

- データ処理プラットフォーム（DuckDB ベース）
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを導入して ETL 実行結果を構造化（取得件数、保存件数、品質問題、エラー等）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）設計をドキュメント化。
    - DuckDB との互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティを実装。
  - src/kabusys/data/etl.py
    - ETLResult を再エクスポートして外部から利用可能に。

- マーケットカレンダー管理
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーを扱うユーティリティ群を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の提供。
    - market_calendar テーブルが未取得の際は曜日ベースでのフォールバック（週末は非営業日）をサポート。
    - calendar_update_job: J-Quants API から差分取得し冪等に保存（fetch/save を jquants_client 経由で呼び出す）。
    - バックフィル、先読み、健全性チェック（未来日付が極端に進みすぎている場合はスキップ）などを実装。
    - 最大探索日数の制限を設けて無限ループを防止。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタムファクター（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20日 ATR）、
      流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）の計算関数を実装。
    - DuckDB SQL を用いた効率的な集計を実装し、データ不足時の None ハンドリングを明示。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（スピアマンのランク相関）calc_ic、
      ランク変換ユーティリティ rank、ファクター統計量 summary を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。
  - src/kabusys/research/__init__.py で主要関数を公開。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）でバッチ評価して ai_scores テーブルへ書き込む機能を実装。
    - 時間ウィンドウ（前日15:00 JST ～ 当日08:30 JST の記事）を厳密に定義し、ルックアヘッドバイアスを防止。
    - バッチサイズ、トリム（記事数・文字数）制限、最大リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンス検証機構（JSON パース、results フォーマット、コード整合性、数値検査）を実装。
    - スコアは ±1.0 にクリップ。部分成功時に既存スコアを保護するため DELETE → INSERT の置換戦略を採用。
    - テスト容易性のため _call_openai_api をパッチ可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次の市場レジームを判定し market_regime テーブルに保存。
    - ma200_ratio の計算、マクロ記事抽出、OpenAI 呼び出し、リトライ、スコア合成、冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 失敗時のフェイルセーフ（macro_sentiment=0.0）とロギングを実装。
    - news_nlp モジュールとは別実装の _call_openai_api を使いモジュール結合を避けている（テストしやすさ）。

Changed
- 設計方針（ドキュメント的追加）
  - 多くのモジュールで「ルックアヘッドバイアスを防ぐ」方針を明確化（date.today() の不使用、クエリの排他条件など）。
  - DuckDB のバージョン差異（executemany の空リスト等）を想定した堅牢な実装に配慮。
  - DB 書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT を期待する jquants_client の設計など）。

Fixed
- 安全性・耐障害性の強化
  - OpenAI API 呼び出しでの 5xx / レート制限 / ネットワーク断 に対するリトライロジックと、最終的に失敗した場合のフェイルセーフ（ログ出力のうえスキップしシステム継続）を導入。
  - JSON レスポンスのパース失敗や余計な前後テキスト混入に対して、復元ロジック（最外の {} 抽出）を追加して実運用での堅牢性を向上。
  - DuckDB の日付型や NULL を扱う際の安全な変換ユーティリティを追加。

Security
- 特記事項なし（公開コードから推測される範囲）。API キーは引数または環境変数（OPENAI_API_KEY 等）で注入する設計で、キーをハードコードしない方針。

Notes / Implementation details
- 単体テスト容易性:
  - OpenAI 呼び出し部分は内部関数をモック/patch できるよう設計している（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- トランザクション安全性:
  - market_regime / ai_scores 等の更新は BEGIN / DELETE / INSERT / COMMIT を用いて冪等かつロールバックを実装。
- 外部 API クライアント:
  - jquants_client や外部保存関数は data パッケージ外部に分離しており、ETL / calendar_update_job から呼び出す設計。
- ロギング:
  - 各モジュールは詳細な logger.debug / logger.info / logger.warning / logger.exception を備え、運用時のトラブルシュートを想定。

Breaking Changes
- なし（初期リリースのため古いバージョンとの互換性問題はなし）。

---- 

今後の改善案（参考）
- ai モジュールのレスポンス検証やスキーマをより厳密に型定義してテストカバレッジを拡充する。
- jquants_client のインタフェース仕様をドキュメント化して ETL の差分取得ロジックを外部化する。
- calendar_update_job の API 呼び出しのリトライやレート制御の実装（現在は例外捕捉でスキップ）。
- 大量データ時のパフォーマンスプロファイリング（DuckDB クエリのインデックスやパーティショニング検討）。

以上。