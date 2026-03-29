# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはまだ初期リリースであり、以下はコードベースから推測して作成した初版リリースノートです。

## [Unreleased]

## [0.1.0] - 2026-03-29

### Added
- パッケージ基礎
  - 初期ライブラリ公開 (`kabusys.__init__`) とバージョン設定: `0.1.0`。
  - パブリック API としてのサブパッケージを定義（data, research, ai, ...）。

- 環境設定/設定管理 (`kabusys.config`)
  - .env/.env.local をプロジェクトルートから自動ロードする仕組みを実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に解決。
  - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを扱えるよう実装。
  - OS 環境変数を保護するための override/protected ロジックを実装。
  - `Settings` クラスを提供し、必要な環境変数取得（J-Quants / kabuステーション / Slack / DB パス等）と値検証（KABUSYS_ENV, LOG_LEVEL）を行う。

- ニュース NLP（AI）機能 (`kabusys.ai.news_nlp`)
  - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチで問い合わせて銘柄ごとのセンチメント（ai_score）を算出する `score_news` を実装。
  - 処理上の特徴:
    - JST 基準のニュース収集ウィンドウ算出（前日 15:00 ～ 当日 08:30 JST → UTC 変換）。
    - 1 銘柄あたりの記事数・文字数上限（肥大化対策）。
    - 最大 20 銘柄/チャンクでバッチ処理（_BATCH_SIZE）。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフとリトライ。
    - OpenAI の JSON Mode を想定したレスポンス検証と堅牢なパース処理（前後ノイズ除去など）。
    - スコアは ±1.0 にクリップ。
    - DuckDB へ冪等的に書き込む（DELETE → INSERT、executemany 使用）。部分失敗でも既存スコアを保護する設計。

- 市場レジーム判定（AI + 指標合成） (`kabusys.ai.regime_detector`)
  - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
  - 特徴:
    - DuckDB の prices_daily/raw_news を参照して計算。
    - マクロ記事はキーワードフィルタリングで抽出（日本・グローバルのマクロ語彙群）。
    - OpenAI 呼び出しに対するリトライ・フェイルセーフ（失敗時は macro_sentiment=0.0）。
    - スコア合成後、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止のために date 比較は排他条件（< target_date）などで実装。

- データ処理 / ETL (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETL の結果を表現するデータクラス `ETLResult` を実装（取得数・保存数・品質問題・エラー等を含む）。
  - 差分取得、バックフィル、品質チェックを想定した設計コメントとユーティリティを用意。
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- マーケットカレンダー管理 (`kabusys.data.calendar_management`)
  - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得→保存）。
  - 営業日判定・前後営業日検索・指定期間内営業日取得・SQ日判定などのユーティリティを提供:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB にカレンダーが無い・未登録日の場合は曜日ベース（平日）でフォールバックする堅牢な設計。
  - 最大探索日数やバックフィル日数、健全性チェック等（設定定数）を導入。

- リサーチ（ファクター計算 / 特徴量探索） (`kabusys.research.*`)
  - ファクター計算モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等を計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。
    - calc_value: PER、ROE を raw_financials と prices_daily から計算。
  - 特徴量探索モジュール:
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）を計算する実装。
    - rank: ランク付け（同順位は平均ランク）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - 実装方針は DuckDB と標準ライブラリに依存し、ルックアヘッドバイアスを避ける設計。

- 依存関係（コードから推測）
  - DuckDB を主要データストアとして利用。
  - OpenAI（openai Python SDK）を LLM 呼び出しに使用。
  - J-Quants クライアント（kabusys.data.jquants_client）を介した外部 API 統合の想定。
  - Slack/Kabu API 関連の設定項目を用意（実際の実装は設定周り）。

- テスト容易性を意識した設計
  - OpenAI 呼び出し部分は内部関数を通じており、unittest.mock.patch による差し替え（モック化）を想定した作り。

### Changed
- 初期リリースのため該当なし（新規実装）。

### Fixed
- 初期リリースのため該当なし（ただし、API 失敗時のフォールバックや入力検証など堅牢性を高める設計を含む）。

### Security
- 環境変数読み込み時に OS 環境変数を上書きしてしまわないよう保護（protected keys）を導入。
- OpenAI API キー未設定時には明確なエラーメッセージを出す。

### Notes / 開発者向けメモ
- 多くの機能は DuckDB と外部 API（OpenAI, J-Quants）に依存するため、本番運用前に API キー・DB スキーマ・テーブル作成（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）の整備が必要です。
- 時間ウィンドウは UTC naive datetime を DB 比較に利用しているため、DB 側の日時（raw_news.datetime 等）は UTC で保存されていることを前提とします。
- 自動 .env 読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後・テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して制御してください。
- API 呼び出し箇所（news_nlp / regime_detector）の _call_openai_api は意図的にモジュールごとに分離されています。モック差し替えはそれぞれのモジュール内関数名を指定してください。

---

（注）本 CHANGELOG は提供されたソースコードから推測して作成したものであり、実際の変更履歴・コミットメッセージとは異なる場合があります。必要であれば、実際の git 履歴やリリースノートの追記に応じて調整できます。