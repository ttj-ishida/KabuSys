# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

なお、この CHANGELOG はコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。主要コンポーネントの実装を含みます。

### 追加
- 基本パッケージ初期化
  - パッケージバージョンを設定 (`kabusys.__version__ = "0.1.0"`)。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動ロードする機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動ロードを実現。
  - export KEY=val 形式やシングル/ダブルクォート、インラインコメント等を含む .env パースを実装。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - 設定取得用の Settings クラスを提供（J-Quants トークン、kabuAPI、LINE、DB パス、監視閾値、環境判定、ログレベルなど）。
  - 必須設定未指定時に ValueError を発生させる `_require` ヘルパーを実装。

- データ処理（kabusys.data）
  - ETL パイプラインのインターフェースを公開（ETLResult）。
  - ETL の結果を表す dataclass `ETLResult` を実装（取得数／保存数、品質チェック、エラー集約、辞書変換メソッド等）。
  - ETL の差分取得・バックフィル・品質チェック設計に基づくユーティリティを実装（pipeline モジュール）。
  - 市場カレンダー管理モジュールを実装（market_calendar を使った営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job）。
    - JPX カレンダー用の夜間バッチ更新（J-Quants からの差分取得）処理を実装。
    - DB 未取得時の曜日ベースフォールバック（週末除外）をサポート。
    - バックフィルや健全性チェック（未来日付閾値）を実装。

- リサーチ（kabusys.research）
  - ファクター計算モジュールを実装（calc_momentum / calc_value / calc_volatility）。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）など。
    - Value: PER / ROE（raw_financials と prices_daily を組み合わせて計算）。
    - Volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等。
    - DuckDB SQL による効率的なウィンドウ集計を採用。
  - 特徴量探索モジュールを実装（calc_forward_returns / calc_ic / factor_summary / rank）。
    - 将来リターン計算（horizons の汎用対応、入力検証）。
    - スピアマン IC（ランク相関）計算（ties は平均ランクで処理）。
    - 基本統計量（count/mean/std/min/max/median）集計ユーティリティ。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメントスコアを取得。
    - 1チャンク最大 20 銘柄（_BATCH_SIZE）でバッチ送信し、1 銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
    - レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 保護（対象コードのみ DELETE → INSERT）を行う。
    - 429 / ネットワーク断 / タイムアウト / 5xx の場合に指数バックオフでリトライする実装。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
    - target_date ベースのニュースウィンドウ計算関数 calc_news_window を提供（JST 時刻を UTC naive に変換して扱う）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュースは raw_news からマクロキーワードでフィルタして最大件数を LLM に送信。
    - OpenAI API 呼び出しのエラーハンドリング（リトライ・フォールバック macro_sentiment=0.0）を実装。
    - OpenAI クライアント生成時に api_key を注入可能。キー未設定時は明示的に ValueError を返す。
    - デザイン方針としてルックアヘッドバイアスを避けるため日時参照を制限。

### 改善（設計上の配慮）
- DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 想定等）して実装。
- DuckDB との互換性を考慮し、executemany に対する空リストバインドを避ける（空チェックを実施）。
- ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を無闇に参照しない実装方針を採用（target_date を引数で明示）。
- エラー時はフェイルセーフで継続する方針（API 失敗時はスコアをスキップまたは 0.0 にフォールバック）。
- ロギングを各モジュールで適切に出力。重要な失敗は例外で伝播しつつ、可能な限り部分結果を保護。

### 既知の注意点 / 制約
- OpenAI API（gpt-4o-mini）を使用する機能は実行に API キー（OPENAI_API_KEY）を必要とする。api_key を関数引数で注入可能（テスト用）。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後や特定のワークフローで想定通りに動作しない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境を設定すること。
- DuckDB のバージョン互換性（特に executemany の空パラメータの挙動）に注意。
- calendar_update_job は J-Quants クライアント（jquants_client）に依存。API 呼び出し失敗時は 0 を返して処理を中断する。

### 修正
- 初回リリースにつき該当なし。

### セキュリティ
- 初回リリースにつき該当なし。ただし OpenAI の API キーや外部トークンは環境変数で管理するよう設計。

---

開発者向けメモ:
- テストの容易性を考慮し、OpenAI 呼び出し箇所（news_nlp._call_openai_api, regime_detector._call_openai_api など）は patch 可能な形で実装されています。ユニットテストでは API 実コールを行わずに挙動確認が可能です。

（この CHANGELOG はコード内容からの推測に基づくため、実際の変更履歴やリリースノートと差分がある可能性があります）