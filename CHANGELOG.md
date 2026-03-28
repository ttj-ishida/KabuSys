# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従い、Semantic Versioning を採用します。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-28

初回リリース。パッケージ全体の基本機能を実装しました。主にデータ取得・ETL・カレンダー管理・研究用ファクター計算・AI を用いたニュース解析と市場レジーム判定を含みます。

### Added
- 全体
  - パッケージ初期版を公開（kabusys v0.1.0）。
  - パッケージエントリポイント: src/kabusys/__init__.py にて __version__ を定義し、主要サブパッケージ（data, research, ai, ...）をエクスポート。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env, .env.local をプロジェクトルート（.git または pyproject.toml）から自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env パーサ実装（export KEY=val 形式、クォート/エスケープ、インラインコメント取り扱いを考慮）。
  - 自動ロード時の OS 環境変数保護（protected セット）と override ロジック。
  - Settings クラスを実装し、必須変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、既定値（KABU_API_BASE_URL, DB パス等）、env/log_level のバリデーション（許容値制限）を提供。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news テーブルのニュースを集約し OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出する score_news を実装。
  - スコア算出の時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
  - バッチ処理（最大 20 銘柄/API コール）、1 銘柄あたりの最大記事数・文字数トリム、JSON Mode を利用したレスポンス検証・バリデーションを実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。
  - レスポンスパース・スキーマ検証を行い、安全に ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込むロジックを実装。部分失敗時に既存スコアを保護する設計。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動）200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - prices_daily からの ma200 比率計算、raw_news からマクロキーワード抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment の評価、閾値に基づくラベリングを実装。
  - API エラー時は macro_sentiment=0.0 とするフェイルセーフ、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - テスト容易性のため OpenAI 呼び出し関数をモジュールローカルに分離。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使用した営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがない場合の曜日ベースのフォールバック、最大探索日数の安全対策、サニティチェックを実装。
    - J-Quants 連携による夜間バッチ calendar_update_job（差分取得、バックフィル、サニティチェック）を実装。
  - ETL / パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラーの集約）。
    - 差分更新・バックフィルの方針、テーブル最終日取得ユーティリティ、DuckDB 互換性に配慮した実装を提供。
    - jquants_client と quality モジュールを組み合わせた ETL フロー設計に対応する基盤を実装（ID トークン注入やエラー収集方針を含む）。

- リサーチ / ファクター（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を用いた PER / ROE 計算（EPS が 0/欠損の場合は None）。
    - DuckDB を用いた SQL ベースの実装。外部 API へはアクセスしない設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（複数ホライズンを一度のクエリで取得）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満は None）。
    - rank: 値をランクに変換（同順位は平均ランク）。
    - factor_summary: 各ファクター列の統計量（count/mean/std/min/max/median）を計算。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

### Fixed / Safety improvements
- ルックアヘッドバイアス対策
  - AI モジュール（news_nlp, regime_detector）とリサーチ関数は datetime.today() / date.today() を内部処理で直接参照せず、target_date で明示的にウィンドウを計算する設計を採用。
  - prices_daily クエリでは target_date 未満（排他）等、データ取得の境界を明示してルックアヘッドを防止。

- リトライとフォールバック
  - OpenAI 呼び出し周りは RateLimit/ネットワーク/タイムアウト/5xx を対象とした指数バックオフリトライを実装。最終的な失敗は安全にフォールバック（例: macro_sentiment=0.0）して処理を継続するように設計。

- DB 書き込みの冪等性とトランザクション保護
  - ai_scores / market_regime 等への書き込みは DELETE → INSERT の形で冪等に実行し、例外時は ROLLBACK を試行。ROLLBACK 失敗時は警告ログを出力。

- DuckDB 互換性対応
  - executemany に空リストを渡すと問題になる事象に対処し、空の場合は実行をスキップする安全ロジックを追加。

- レスポンスバリデーション強化
  - LLM レスポンスの JSON パース失敗や余計な前後テキストに対する保険処理（最外の {} を抽出して復元）を実装。
  - news_nlp 側では返却された code を文字列化して照合し、整数で返されるケースにも対応。

### Security
- 環境変数ロード時に OS 環境を保護する設計（既存の OS 環境変数を上書きしない、.env.local で明示的オーバーライド可能）。
- OpenAI API キーは引数による注入または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を発生させる仕様（不注意な運用を防止）。

### Known limitations / Not implemented
- calc_value では PBR・配当利回りは未実装（将来の拡張余地）。
- AI モデルは gpt-4o-mini を想定。将来的なモデル差し替えや API 仕様変更に備えた抽象化は今後の課題。

### Breaking Changes
- 初回リリースのため該当なし。

---

このリリースは、データ取得/ETL/カレンダー管理からリサーチ向けのファクター計算、さらに OpenAI を使ったニュース解析・市場レジーム判定までを一通りカバーする基盤を提供します。今後のリリースでは性能改善、追加ファクター、追加品質チェック、外部 API の耐障害性向上などを予定しています。