CHANGELOG
=========

すべての重要な変更を記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。  

注: 以下はソースコードの内容から推測して作成した初回リリース向けの変更履歴です。

Unreleased
----------

- なし

0.1.0 - 2026-03-31
------------------

初期公開リリース。日本株自動売買プラットフォームの基盤的機能群を実装。

Added
-----

- パッケージの基本構成を追加
  - kabusys パッケージのエントリーポイントを追加（src/kabusys/__init__.py、バージョン: 0.1.0）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に基づく公開方針）。

- 環境変数／設定管理（src/kabusys/config.py）
  - Settings クラスを実装し、アプリケーション設定を環境変数から取得する API を提供。
  - 必須項目のチェック（_require）を実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - DuckDB / SQLite のデフォルトパス（DUCKDB_PATH, SQLITE_PATH）を提供。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装。
  - .env パーサーを実装し、quotes・エスケープ・export プレフィックス・コメント処理に対応。
  - .env 読み込み時に OS 環境変数の保護（protected set）と .env.local による上書き処理を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメント集約（news_nlp）
    - calc_news_window によるニュース収集ウィンドウ計算（JST基準 → UTC変換）。
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI に送信。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄あたりの記事数・文字数制限、JSON Mode を利用した出力のバリデーションを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数的バックオフ・リトライ処理。
    - レスポンスの堅牢なパース（余分なテキストが混ざる場合の {} 抽出）とスコアの±1.0クリップ。
    - ai_scores テーブルへの冪等的な書き込み（DELETE → INSERT、部分失敗時の保護）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロニュース由来の LLM センチメント（重み30%）を合成して日次で市場レジームを判定（bull/neutral/bear）。
    - prices_daily / raw_news / market_regime を使用してスコア計算・冪等的書き込みを実行。
    - OpenAI 呼び出しに対するリトライとエラー時のフォールバック（macro_sentiment=0.0）。
    - LLM 用のプロンプト（厳密な JSON 出力指示）とレスポンス処理を実装。
    - テスト時に差し替え可能な _call_openai_api を提供。

- データ管理（src/kabusys/data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを基にした is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベース（平日のみを営業日）でフォールバックする堅牢なロジック。
    - 最大探索日数制限や健全性チェック、バックフィル戦略を実装。
    - calendar_update_job による J-Quants API からの差分取得＆保存フロー（フェイルセーフなログと 0 戻り値で失敗を示す）。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを追加して ETL 実行結果の集約（取得数・保存数・品質問題・エラー）を提供。
    - 差分取得、バックフィル（既定3日）、市場カレンダーの先読みなどのルールを実装。
    - 品質チェック（quality モジュール）との連携を想定したエラー収集設計（Fail-Fast ではない）。

- リサーチ（src/kabusys/research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（DuckDB SQL ベース）。
    - calc_volatility: 20 日 ATR（平均）・相対 ATR、20 日平均売買代金、出来高比率の計算。
    - calc_value: raw_financials から EPS/ROE を取り出し PER/ROE を計算（直近報告を参照）。
    - いずれも prices_daily / raw_financials のみを参照し、外部 API にはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算する関数を提供。
    - rank: 同順位は平均ランクとするランク化ユーティリティを実装（丸め対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する集計ユーティリティ。

Changed
-------

- 設計上の方針（ドキュメントコメントとして明記）
  - 全ての LLM / ニュース / レジーム / リサーチ関連関数は datetime.today() / date.today() に依存せず、target_date を明示的に受け取ることでルックアヘッドバイアスを回避。
  - DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装（空リストチェックを追加）。
  - OpenAI 呼び出しの失敗は基本的に例外で落とさずフォールバックして処理継続する方針（安全性重視）。
  - モジュール間でのプライベート関数共有を避ける（各モジュールで独自の _call_openai_api を実装）。

Fixed / Improved
----------------

- .env パーサーの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理の改善を実装。
  - .env ファイルの読み込み失敗時に warnings.warn で通知してプロセスを継続する挙動に。
- OpenAI レスポンスのパース耐性強化
  - JSON decode 失敗時に文字列内の最外側の { ... } を抽出して再パースする手当てを追加。
  - APIError の status_code を安全に取得して 5xx/非5xx を判別しリトライ判定に利用。
- DB 書き込みの冪等性とロールバック処理
  - market_regime / ai_scores 書き込みは BEGIN / DELETE / INSERT / COMMIT のパターンで冪等に実行し、例外時は ROLLBACK を試行してから例外を再送出。
  - ROLLBACK 自体の失敗をログ出力して監視しやすくした。

Security
--------

- 環境変数の保護
  - .env 読み込み時に既存の OS 環境変数を protected として上書きから保護。
  - LLM を利用する関数は api_key を引数で注入でき、環境変数 OPENAI_API_KEY を使用する際も明示的に要求する（未設定時は ValueError）。
- 自動ロード抑止
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で .env の自動ロードを無効化可能。

Testing / Developer friendliness
-------------------------------

- OpenAI 呼び出しをモックしやすい設計（各モジュールに _call_openai_api を定義し、unittest.mock.patch で差し替え可能）。
- ETLResult.to_dict で品質問題のサマリをログ／監査に容易に出力可能。

Known limitations / Notes
-------------------------

- ai_scores/market_regime のテーブルスキーマ・jquants_client 実装・quality モジュール実体はこの差分内では示されていません。実運用には対応する DB スキーマと外部クライアント実装が必要です。
- OpenAI との通信は gpt-4o-mini を想定した実装（モデル名を定数化）。利用するモデルの互換性変更時はプロンプトやレスポンスパースの見直しが必要です。
- calc_value は現時点で PBR・配当利回りをサポートしていません（将来的機能追加の余地あり）。
- DuckDB 特有の SQL バインディングや型変換の違いに依存しているため、他の DB への移植には追加作業が必要です。

Breaking Changes
----------------

- なし（初回リリースのため後方互換性に関する記載はありません）。

Deprecated
----------

- なし

Removed
-------

- なし

---

今後のリリースでは、以下が予定される可能性があります（コードからの推測）:
- ai_scores のスキーマ拡張（複数スコアやメタデータの保存）
- 追加のファクター（PBR・配当利回りなど）や、リサーチの可視化ユーティリティ
- jquants_client の具体的な実装例と API レート制御の強化
- エンドツーエンドのデータパイプラインジョブと運用ドキュメントの追加

もし特定のファイルごと／機能ごとの詳細な変更履歴や、日付を他にしたい場合は指示してください。