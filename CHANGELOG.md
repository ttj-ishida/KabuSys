# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルは、与えられたコードベースから推測できる変更点・リリース内容を日本語で整理したものです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース（推定）。本バージョンで導入された主な機能と設計方針をモジュール別に記載します。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ に定義）

- 設定・環境変数管理（kabusys.config）
  - Settings クラスを導入し、J-Quants／kabuステーション／Slack／DB／監視などの設定を環境変数からプロパティとして取得可能に。
  - .env 自動ロード機構:
    - プロジェクトルートを .git または pyproject.toml を探索して判定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースは export 形式、クォート、コメント（#）等に対応する堅牢な実装。
  - 必須環境変数が未設定の場合は ValueError を送出する _require 関数を提供。
  - 環境（development / paper_trading / live）やログレベルの検証ロジックを実装。

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを計算。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC での変換を内部で実施）。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事数・文字数上限を導入（トークン肥大対策）。
    - レスポンスのバリデーション（JSON 抽出、results 配列、コード照合、スコア数値検証）と ±1.0 クリップ。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）＋指数バックオフ実装。フェイルセーフ：失敗時は該当チャンクをスキップして続行。
    - DB 書き込みは冪等性を確保（DELETE → INSERT の順）し、部分失敗時にも既存スコアを保護。
    - テスト用フック: _call_openai_api を patch してモック可能。
    - 公開 API: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用、データ不足時は中立 1.0 を返す）。
    - raw_news からマクロキーワードで記事タイトルを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を評価。
    - LLM 呼び出しは独立実装、リトライとフェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB に market_calendar がない・未登録日は曜日ベース（平日）でフォールバック。
    - next/prev_trading_day は最大探索範囲制限（_MAX_SEARCH_DAYS）を設けて無限ループ回避。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル（直近 _BACKFILL_DAYS 再取得）と健全性チェックを実装。
    - jquants_client 依存のフェッチ/保存処理を呼び出す。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー情報を集計）。
    - 差分取得のための最小データ日付、バックフィル、品質チェックの設計方針を実装。
    - ETLResult.to_dict により品質問題を辞書化して監査ログに対応。
    - pipeline のユーティリティ（テーブル存在チェック、最大日付取得等）を一部実装。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日 MA 乖離率）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS=0/欠損は None）。
    - 設計方針: DuckDB 上の SQL で完結、ルックアヘッドを防ぐ実装。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon（営業日）に対する将来リターン（fwd_1d, fwd_5d, fwd_21d 等）を一括 SQL で取得。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足時は None を返す。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ（round で丸めて ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーは関数引数で注入可能（テスト容易性と秘匿の選択肢を提供）。環境変数 OPENAI_API_KEY を使うデフォルト挙動もあり。

### 設計上の注意点・フェイルセーフ
- ルックアヘッドバイアス防止: 日付計算で datetime.today()/date.today() を直接参照しない実装指針が明示され、各処理で target_date を明示的に与える設計になっている。
- 外部 API 呼び出しの堅牢化: リトライ（指数バックオフ）、5xx の扱い、JSON パース失敗時のフォールバック（スコア = 0.0）等。
- DB 書き込みの冪等性を優先（DELETE → INSERT、トランザクション、ROLLBACK ハンドリング）。
- テストフレンドリーな設計: OpenAI 呼び出し部分にモック差し替えフックを用意。

### 既知の問題 (Known issues)
- 提供されたコード断片の末尾において、kabusys.data.pipeline._get_max_date 関数が途中で切れている（"return date.fro" のような不完全な行が存在）。実運用前に当該箇所の実装確認・修正が必要です（本 CHANGELOG は与えられたスナップショットから推測して作成しています）。
- 一部モジュール（strategy, execution, monitoring）の実体がこのスナップショット内で含まれていないため、パッケージ公開 API に対して実装が不足している可能性がある点に注意してください。

---

この CHANGELOG は、提示されたソースコードの内容から実装機能・方針を推測して作成しています。実際のリリースノートを作成する際は、Git のコミット履歴・リリースマネージャの意図・未コミットの差分等も合わせて確認してください。