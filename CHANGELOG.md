Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。これは Keep a Changelog のガイドラインに準拠します。
リリースは逆時系列で並びます。

[Unreleased]
------------

- なし（初期リリース）

[0.1.0] - 2026-03-28
-------------------

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点と設計上の留意点は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージ初期実装（__version__ = 0.1.0、公開モジュール指定）。
- 環境設定
  - kabusys.config: .env ファイルと OS 環境変数の読み込み機能を追加。
    - プロジェクトルート自動検出（.git / pyproject.toml を探索）。
    - .env / .env.local の読み込み順序、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - export 形式・クォート・インラインコメント対応の堅牢なパーサ。
    - Settings クラス：J-Quants、kabu API、Slack、DB パス、環境（development/paper_trading/live）、ログレベル等のプロパティとバリデーション。
- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を用いた銘柄ごとのニュース集約と OpenAI（gpt-4o-mini）によるバッチセンチメント評価。
    - タイムウィンドウ計算（JST基準で前日15:00〜当日08:30）と記事トリミング（最大記事数・文字数制限）。
    - JSON Mode を利用した応答バリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx 対応の指数バックオフリトライ。
    - テスト用の差し替え（_call_openai_api を patch 可能）を考慮した実装。
    - ai_scores テーブルへの冪等的書き込み（DELETE → INSERT）事前の空チェック（DuckDB executemany の互換性対策）。
  - kabusys.ai.regime_detector
    - 日次で市場レジーム（bull/neutral/bear）判定ロジックを追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来マクロセンチメント（重み 30%）を合成。
    - OpenAI 呼び出しに対する堅牢なリトライ、フェイルセーフ（API失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理。
- Data / ETL / カレンダー
  - kabusys.data.pipeline / etl
    - ETLResult データクラス（ETL 実行結果の集約）を公開。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）の設計を反映。
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar）の夜間バッチ更新 job と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得時の曜日ベースのフォールバック、最大探索範囲リミット、健全性チェック、バックフィル等の安全策を実装。
  - kabusys.data.jquants_client 想定の差分取得・保存フックと連携する設計（fetch/save 呼び出しを想定）。
- Research（ファクター計算・特徴量探索）
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリューファクター（PER/ROE）などの計算関数を追加。
    - DuckDB SQL を利用して、prices_daily / raw_financials のみ参照する設計。
    - データ不足時は None を返す堅牢な実装。
  - kabusys.research.feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（スピアマンランク相関）計算、ランク化ユーティリティ、factor_summary（統計サマリー）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。
- その他実装上の配慮
  - 全体設計で「ルックアヘッドバイアス防止」を優先（datetime.today()/date.today() の直接参照を避け、呼び出し側で target_date を指定）。
  - OpenAI 呼び出しの失敗を全体の停止に繋げないフェイルセーフ（多くの箇所で 0.0 戻し・スキップ処理を採用）。
  - DuckDB のバージョン差異を考慮した SQL / executemany の互換性対策。
  - ロギング（適切な情報/警告/例外ログ）と安全なロールバック処理を通じた耐障害性。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を発生させ検出しやすくしています。
- 環境変数自動ロード時に OS の既存環境変数は protected として上書きを防止。

Notes / Known issues
- OpenAI 依存部分は外部ネットワーク呼び出しを行うため、API 利用料・レート制限・キー管理に注意してください。
- DuckDB のバインド挙動やバージョン差異に依存する箇所があるため、運用環境での DuckDB バージョン互換性確認を推奨します。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布パッケージ環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して明示的に管理することを推奨します。
- gpt-4o-mini（JSON Mode）からの応答に余計な前後テキストが含まれるケースに対する復元処理を実装していますが、応答フォーマットの厳密性は API 側の挙動に依存します。

Contributing
- バグ修正、改善提案、テスト追加は歓迎します。AI API 呼び出し部分は unit test で _call_openai_api を patch しやすい設計にしています。

----