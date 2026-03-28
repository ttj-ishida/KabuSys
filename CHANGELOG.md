# Changelog

すべての注記は Keep a Changelog のガイドラインに準拠します。  
このファイルにはリリースごとの主な追加・変更・修正点を記載しています。

- リリース履歴は semver に基づきます。  
- 日付は YYYY-MM-DD 形式で記載しています。

## [Unreleased]

---

## [0.1.0] - 2026-03-28

最初の公開リリース。日本株自動売買／データ基盤のコア機能群を実装しました。  
以下はコードベースから推測される主要な追加点と設計上の注記です。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン番号を設定（__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を基準）。
  - 柔軟な .env パーサを実装（export プレフィックス対応、クォートとバックスラッシュエスケープ、行内コメントの扱い等）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し主要設定値をプロパティとして取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development / paper_trading / live の検証)
    - LOG_LEVEL（有効値検証）
    - is_live / is_paper / is_dev の簡易判定プロパティ
  - 必須環境変数未設定時は ValueError を送出するヘルパ（_require）。

- データアクセス / ETL（kabusys.data.pipeline / etl）
  - ETLResult データクラスを実装し、ETL 実行結果（取得件数、保存件数、品質問題、エラー一覧等）を集約。
  - 差分取得・バックフィル・品質チェックの設計方針を実装（J-Quants クライアント経由での取得を想定）。
  - DuckDB の存在チェックやテーブル最大日付取得ユーティリティを実装。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar を利用した営業日判定ロジックを実装：
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
  - DB データが部分的にしかない場合の「DB 値優先・未登録日は曜日ベースでフォールバック」アルゴリズムを採用。
  - calendar_update_job を実装し J-Quants からの差分取得と冪等保存（バックフィルと健全性チェック含む）を行う。
  - 最大探索日数やバックフィル幅等の安全パラメータを定義（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS など）。

- 研究・ファクター計算（kabusys.research）
  - factor_research モジュールで以下の定量ファクター計算を実装：
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None または中立扱い）
    - calc_volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比率
    - calc_value: PER、ROE（raw_financials から最新報告を取得）
  - feature_exploration モジュールで以下を実装：
    - calc_forward_returns: 任意ホライズンの将来リターン取得（horizons 検証あり）
    - calc_ic: スピアマンランク相関に基づく IC 計算（3 銘柄未満は None）
    - rank: 平均ランク（同順位は平均ランク）を算出
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算
  - zscore_normalize を含むデータ系ユーティリティと連携可能な構成。

- AI / ニュース NLP（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）に送信し ai_scores に書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり最大記事数・文字数制限、JSON Mode を用いた厳格なレスポンス検証を実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフ、レスポンス検証（JSON 抽出、results リスト、code と score の検証、スコアの有限性チェック、±1.0 でクリップ）を実装。
    - DuckDB executemany の空リスト制約に対応する安全な DB 書き換え（DELETE→INSERT）を採用し、部分失敗時に他銘柄の既存データを保護。
    - テスト容易性のため _call_openai_api を patch 可能（モック差し替えを想定）。
  - regime_detector モジュール:
    - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出用キーワード群を定義（日本・米国・グローバル混在）。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数共有しない）で、API のリトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - レジームスコアのしきい値（_BULL_THRESHOLD, _BEAR_THRESHOLD）を定義。

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### 既知の挙動 / 設計上の注意（Notes）
- ルックアヘッドバイアス防止:
  - 多数のモジュール（news_nlp, regime_detector, research 等）は datetime.today()/date.today() による自動参照を避け、すべて target_date 引数ベースで処理を行う設計になっています。
- フェイルセーフ挙動:
  - LLM 呼び出し失敗時に処理を継続する（スコアは 0.0 または該当銘柄はスキップ）。これにより ETL/分析処理が LLM の一時障害で全停止しない設計です。
- OpenAI API:
  - API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照します。未設定の場合は ValueError を送出。
  - JSON Mode を使用しつつも、稀に混入する前後テキストを復元するロジックを備えています。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮した防御実装があります。
- カレンダー & 営業日:
  - market_calendar が部分的にしかない場合でも一貫した挙動を返すよう DB 優先 + 曜日フォールバックを採用しています。
- テスト性:
  - OpenAI 呼び出し部分はモック差し替え可能に実装されておりユニットテストが行いやすくなっています。

### セキュリティ（Security）
- （初回リリースのため該当なし）

---

今後のリリースでは以下が想定されます（例）:
- strategy / execution / monitoring モジュールの具現化（注文発注ロジック、ポートフォリオ管理、監視アラート等）
- より詳細な品質チェックルールの追加（quality モジュール拡張）
- テストカバレッジと CI の整備、パフォーマンス最適化

もし CHANGELOG に追加したい詳細（日付、担当、実装の差分など）があれば教えてください。必要に応じて各コミットや差分に基づくより精緻な項目を作成します。