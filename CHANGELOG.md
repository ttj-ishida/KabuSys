# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このプロジェクトはまだ初期バージョンのため、過去リリースはありません。以下はコードベース（src/kabusys 以下）から推測して作成した初回リリースの変更履歴です。

全般的な方針・設計上の重要事項
- ルックアヘッドバイアス防止のため、日付関連処理は datetime.today() / date.today() を直接参照せず、明示的な target_date をパラメータとして受け取る設計になっています。
- DuckDB を内部データストアとして利用。DB 書き込みは可能な限り冪等（DELETE→INSERT / ON CONFLICT 相当）で行うよう配慮されています。
- OpenAI（gpt-4o-mini）呼び出しを使用する機能は、リトライ（指数バックオフ）・レスポンスバリデーション・フォールバック（API 失敗時は中立スコアで継続）を備えた堅牢設計です。
- テスト容易性のため、OpenAI 呼び出しラッパー関数はモジュール内で分離されており、unittest.mock.patch による差し替えが可能です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-03
初回公開（推測）。以下の主要機能・モジュールを含みます。

Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ に登録）。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - export KEY=val 形式やクォート、インラインコメントを扱う堅牢な .env パーサを実装。
  - Settings クラスを提供し、アプリケーション設定（J-Quants、kabu API、LINE、DB パス、監視閾値、環境モード、ログレベル判定等）をプロパティ経由にて取得可能。
  - 必須環境変数未設定時は ValueError を発生させる _require() を実装。

- ニュース NLP（AI） (src/kabusys/ai/news_nlp.py)
  - score_news(conn, target_date, api_key=None): raw_news と news_symbols を元に銘柄単位のニュースを集約し、OpenAI にバッチで送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む。
  - タイムウィンドウ計算（calc_news_window）：JST の前日 15:00 ～ 当日 08:30 を UTC に変換して利用。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりの記事数・本文長のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大を抑止。
  - OpenAI 呼び出しに対するリトライ（429・ネットワーク断・タイムアウト・5xx を対象）、レスポンスの JSON バリデーション、スコアの ±1.0 クリップ。
  - レスポンスパース失敗や API 例外時は該当チャンクをスキップし、他銘柄処理を継続（フェイルセーフ）。
  - DuckDB への書き込みは部分成功を考慮し、該当コードのみ DELETE → INSERT の形で置換（部分失敗時に既存データの保護を実現）。
  - テスト容易性のため _call_openai_api をモジュール内で分離（patch 可能）。

- 市場レジーム判定（AI + 指標ミックス） (src/kabusys/ai/regime_detector.py)
  - score_regime(conn, target_date, api_key=None): ETF 1321（Nikkei ETF）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込み。
  - MA200 乖離計算（_calc_ma200_ratio）は target_date 未満のデータのみを使用し、データ不足時は中立（1.0）を返す。
  - マクロニュース抽出（_fetch_macro_news）はキーワードベースのフィルタを実装（_MACRO_KEYWORDS）。
  - OpenAI 呼び出しは独自実装でリトライ・エラー処理を行い、API 失敗時は macro_sentiment=0.0 として継続（ログを出力）。
  - 最終的なスコアはクリップされ閾値により label を決定、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT で冪等に実行。失敗時は適切に ROLLBACK を試みる。

- データ基盤（Data） (src/kabusys/data/*.py)
  - calendar_management.py
    - JPX マーケットカレンダー管理。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の API を提供。
    - market_calendar が未取得の場合は曜日ベース（土日を非営業日）でフォールバックする一貫した判定ロジック。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を更新（バックフィル・健全性チェックを実施）。
    - 最大探索日数やバックフィル等の安全対策を実装。
  - pipeline.py / etl.py
    - ETLResult データクラス（ETL 実行結果、品質問題・エラー集約、to_dict 変換）を提供。
    - ETL の差分取得・保存・品質チェックの方針をコードに反映（_MIN_DATA_DATE、backfill、品質チェックの収集方針など）。
    - jquants_client 呼び出しを通じた idempotent な保存処理を想定。

- 研究用（Research） (src/kabusys/research/*.py)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを取り、PER（EPS が 0/欠損時は None）、ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、本番発注等に影響しない設計。
  - feature_exploration.py
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（有効レコード 3 未満で None を返す）。
    - rank: 同順位の平均ランク化（round で丸めて ties 対応）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- テスト/運用支援
  - OpenAI 呼び出しの差し替えポイント（_call_openai_api）を各 AI モジュールで用意し、ユニットテストでモック可能にしています。
  - ログ（logger）を各モジュールに配置し、処理の状態・フォールバック・API エラーを適切に記録します。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。多数のエラー条件（API/JSON/DB 書き込み等）に対するフォールバックや警告ログが実装されています。

Security
- OpenAI / 外部 API キーは環境変数（OPENAI_API_KEY など）から読み込む仕様。Settings._require により必須設定の未設定はエラー化されます。機密情報は .env / OS 環境変数で管理する想定。

Notes / Known limitations
- OpenAI（gpt-4o-mini）に依存する機能は API 利用料とレイテンシが発生します。API 利用失敗時はフェイルセーフとして中立スコア・スキップ処理を行いますが、期待する品質が得られない可能性があります。
- jquants_client（jquants API）や実際の DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials 等）はこのコードから参照されていますが、これらの実体（クライアント実装・テーブル定義）は別途整備が必要です。
- strategy / execution / monitoring モジュールは __all__ に名前が含まれていますが、この差分には具体実装が含まれていない（または別ファイル）可能性があるため、運用フローや発注ロジックは別途確認が必要です。

Upgrade notes
- 本リリースでは後方互換性を意識した設計を行っています。将来的に API（関数シグネチャ）を変更する際には、Settings と AI モジュールの api_key 解決方法、DuckDB テーブル名・スキーマの変更に注意してください。

---

この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートやバージョン管理履歴がある場合はそれに合わせて最終調整してください。必要であれば、各機能ごとにより詳細な変更点（関数・定数一覧、引数仕様、例外・返り値の詳細）を生成します。どのレベルの詳細が必要か指示してください。