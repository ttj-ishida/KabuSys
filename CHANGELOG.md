# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-27

### 追加 (Added)
- 基本パッケージ初期実装
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 環境設定 / ロード周り
  - .env ファイルおよび環境変数から設定を読み込む `kabusys.config` モジュールを追加。
  - プロジェクトルートの自動検出（`.git` または `pyproject.toml` を基準）を実装し、カレントワーキングディレクトリに依存しない自動 .env ロードを実現。
  - .env パーサ (`_parse_env_line`) を実装：コメント行、`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 自動読み込みの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `Settings` クラスを提供（J-Quants / kabu API / Slack / DB パス / ログレベル / 環境判定などのプロパティを含む）。必須環境変数取得時の検査（未設定時は ValueError）。

- AI（LLM）連携機能
  - ニュースセンチメントスコアリングモジュール `kabusys.ai.news_nlp`
    - raw_news と news_symbols から記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - チャンク処理（最大 20 銘柄 / バッチ）、1銘柄あたりの記事数・文字数上限（肥大化対策）を実装。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフを実装。API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - OpenAI レスポンスのバリデーション（JSON 抽出、results リスト、既知コード照合、数値変換、スコアクリップ）を実装。部分的に不正なレスポンスでも安全に扱う。
    - DuckDB への書込みは冪等性を保つ（DELETE → INSERT）。DuckDB の executemany 空リスト制約に配慮。
    - テスト用に OpenAI 呼び出し部分を patch できるフック（`_call_openai_api`）を用意。
    - メイン公開関数: `score_news(conn, target_date, api_key=None)`。

  - 市場レジーム判定モジュール `kabusys.ai.regime_detector`
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して `market_regime` テーブルへ保存。
    - LLM 呼び出しは独立実装で `gpt-4o-mini` を使用。記事が存在しない場合は LLM コールをスキップし macro_sentiment=0.0 として継続。
    - 再試行・バックオフ・5xx とそれ以外のエラーの扱いを明確化。API 失敗やパース失敗は警告ログを出しデフォールト値へフォールバック（例外は投げない）。
    - DB への書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - メイン公開関数: `score_regime(conn, target_date, api_key=None)`。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン共通インターフェース `kabusys.data.pipeline`
    - ETL 実行結果を表す `ETLResult` データクラスを導入（取得件数、保存件数、品質問題、エラーの収集とシリアライズ等）。
    - 差分取得・バックフィル・品質チェックの設計方針を反映。

  - カレンダー管理モジュール `kabusys.data.calendar_management`
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job`（J-Quants API 経由で市場カレンダーを取得し冪等保存）。
    - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB にデータがない場合は土日ベースのフォールバックを採用。
    - データの健全性チェック、バックフィル、最大探索日数上限の実装により無限ループや異常データを防止。
    - jquants_client 経由の fetch/save フックを利用。

  - ETL ユーティリティの公開（`kabusys.data.etl` は pipeline.ETLResult を再エクスポート）

- リサーチ / ファクター分析
  - `kabusys.research.factor_research`
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB 上で計算する関数群（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - DuckDB SQL とウィンドウ関数を用いた実装。データ不足時の None 処理やログ出力を実装。

  - `kabusys.research.feature_exploration`
    - 将来リターン計算（`calc_forward_returns`）、IC（Spearman ρ）計算（`calc_ic`）、ランク変換（`rank`）、統計サマリー（`factor_summary`）を提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。入力検証・境界条件チェックあり。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いに関して明確化：
  - API キーは関数引数で注入可能。未指定時は環境変数 `OPENAI_API_KEY` を参照。
  - 環境設定での必須キーは `Settings` にて ValueError を出す挙動を導入し、実行時に意図しない未設定を防止。

### 注意事項 / マイグレーションノート (Notes)
- 環境変数
  - 本システム稼働には最低限以下の環境変数が必要になる可能性があります（Settings プロパティ参照）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出しを行う機能を使う場合）など。
  - 自動 .env ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB 互換性
  - DuckDB のバージョン差異（executemany に空リストを渡せない等）を考慮した実装になっています。DuckDB のバージョンにより細かな挙動差が出る可能性があります。

- LLM 呼び出し
  - OpenAI（gpt-4o-mini）を JSON Mode で利用する実装のため、レスポンスの仕様変更や API SDK 更新によりエラーが発生する可能性があります。API エラーに対してはフェイルセーフ（0.0 やチャンクスキップ）で継続する設計です。

- ルックアヘッド対策
  - ニュース / レジーム / ファクター計算などで「現在時刻参照」を避け、与えられた target_date を基準に過去データのみを参照する設計（ルックアヘッドバイアス防止）を採用しています。

- テスト性
  - OpenAI 呼び出し部分などは内部関数をモック/パッチしやすいように分離されています（ユニットテストの容易化）。

---

開発・運用中に新しい変更が加わった場合は、本 CHANGELOG を更新していきます。必要であればリリース単位（Unreleased → バージョン）で分けて記載してください。