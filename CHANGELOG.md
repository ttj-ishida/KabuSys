# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。

## [0.1.0] - 2026-03-28

初回リリース。本パッケージは日本株のデータ取得・ETL・特徴量算出・市場レジーム判定・ニュースNLP 等を一貫して提供するライブラリとして実装されています。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0、公開 API の __all__ 定義）。
- 設定・環境変数管理 (`kabusys.config`)
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env / .env.local の優先順位処理（OS 環境変数を保護する protected セット）。
  - .env パーサーの強化：コメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープを正しく処理。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API 設定、Slack 設定、DB パス、環境/ログレベル検証、is_live/is_paper/is_dev 判定等）。
  - デフォルト値（KABUSYS_ENV="development"、LOG_LEVEL="INFO"、DUCKDB_PATH/SQLITE_PATH の既定パス）と検証ロジックを実装。
- AI（LLM）機能 (`kabusys.ai`)
  - ニュースNLP (`kabusys.ai.news_nlp`)
    - score_news 関数を実装：raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores テーブルへ保存。
    - タイムウィンドウ計算（calc_news_window）：JST 基準で前日 15:00 〜 当日 08:30 を対象（内部は UTC naive datetime）。
    - バッチ処理（最大 20 銘柄/チャンク）、記事トリミング（最大記事数 & 最大文字数）、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ。
    - ネットワーク/429/タイムアウト/5xx に対する指数バックオフ・リトライ、失敗時は安全にスキップして継続。
    - DuckDB executemany の空リスト問題へ対応（空パラメータは実行しない）。
    - テスト容易性を考慮し、内部 OpenAI 呼び出し関数をパッチ可能に実装。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - score_regime 関数を実装：ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とニュース（LLM）センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる記事フィルタリング、OpenAI 呼び出しのリトライ/フォールバック（API 失敗時は macro_sentiment=0.0）。
    - LLM 出力の JSON パースと安全なクリップ処理。
- データプラットフォーム機能 (`kabusys.data`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した振る舞い。
    - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェック実装）。
    - 最大探索日数制限や将来日付の健全性チェックなど安全策を実装。
  - ETL パイプライン (`kabusys.data.pipeline` / `kabusys.data.etl`)
    - ETLResult dataclass を実装して ETL の集約結果（フェッチ数、保存数、品質問題、エラー等）を返却。
    - 差分更新、バックフィル、品質チェック（quality モジュール呼び出し想定）に対応する設計。
    - J-Quants クライアント（jquants_client）経由での差分取得 & idempotent 保存を想定。
    - DuckDB 用ユーティリティ（テーブル存在確認、最大日付取得など）。
- リサーチ（特徴量・因子）機能 (`kabusys.research`)
  - 因子計算 (`kabusys.research.factor_research`)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率の計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を参照して PER/ROE を計算（EPS が 0/NULL の場合は PER を None）。
    - DuckDB SQL を中心に実装し、外部 API や発注には触れない設計。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - calc_forward_returns: 任意ホライズンの将来リターンをまとめて取得（ホライズン検証あり）。
    - calc_ic: Spearman ランク相関（IC）計算（結合・欠損除外・最小サンプルチェック）。
    - rank: 同順位を平均ランクで処理するランキング実装（丸めによる ties 対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
- テスト性・運用性
  - OpenAI 呼び出し部分はテストで差し替え可能（patch しやすい内部関数）。
  - ロギングを各モジュールに実装し、異常系での情報出力や警告を充実。
  - DuckDB 特有の挙動（executemany の空リスト等）を考慮した実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の注意点 / 制限
- OpenAI API（gpt-4o-mini）に依存する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要。キー未設定時は ValueError を送出して呼び出し元に明示。
- DuckDB を前提として実装（DuckDB のバージョン差異に対する互換性考慮あり）。
- ai_scores / market_regime 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）だが、DB 側の制約や接続エラー時は例外が上位へ伝播する。
- 一部の算出関数は入手データ不足時に None を返す設計（呼び出し側での取り扱いに注意）。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や実行環境により挙動が変わる可能性あり。必要であれば KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### セキュリティ (Security)
- 環境変数（API キー等）は OS 環境変数が優先され、.env の値は既存の OS 環境値を上書きしない（.env.local は上書き可だが OS 環境は保護）。
- .env ファイルの読み込み失敗時は警告を出し処理継続（例外は送出しない）。

---

今後のリリースでは、文書化の拡充、追加の品質チェックルール、J-Quants クライアントの詳細実装、バックテスト / 実運用のためのモジュール（注文執行・モニタリング等）の公開を予定しています。