# CHANGELOG

本ファイルは Keep a Changelog の形式に準拠しており、重要な変更点を日本語で記録します。  
バージョン番号はパッケージの __version__ を基にしています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初回リリース。

### 追加 (Added)
- パッケージ構成を追加
  - kabusys パッケージの公開 API として data / strategy / execution / monitoring を意図的に公開（src/kabusys/__init__.py）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数からの設定読み込みを実装。プロジェクトルートの自動検出（.git または pyproject.toml）に基づく自動ロード機能を提供。
  - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサー実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理に対応。
  - Settings クラスを実装し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供。
  - 必須環境変数未設定時に ValueError を送出する _require を提供。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を実装。
  - 各種監視閾値（CPU/MEMORY/DISK）や PID/KILL フラグの設定プロパティを追加。

- ニュースNLP（AI） (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント ai_score を算出する機能を実装。
  - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）とそれに対応する calc_news_window 関数を提供。
  - バッチ処理（1 API 呼び出しで最大 20 銘柄）・記事数制限（銘柄当たり最大 10 記事）・文字数トリム（最大 3000 文字）を実装。
  - OpenAI 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）と、JSON 応答の堅牢なパース・バリデーションを実装。
  - レスポンス検証ロジックにより不正/未知コードは無視し、スコアを ±1.0 にクリップ。
  - スコア書き込みは冪等的に実行（対象コードのみ DELETE → INSERT、トランザクション管理）し、部分失敗時に他コードの既存スコアを保護。
  - score_news(conn, target_date, api_key=None) を公開。APIキー未設定時は ValueError を送出。

- 市場レジーム判定（AI + 指標合成） (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジームを日次判定する score_regime 関数を実装。
  - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini / JSON mode）、リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
  - MA 計算のデータ不足時は ma200_ratio=1.0（中立）を返す設計。
  - 合成スコアを基に regime_label を bull/neutral/bear に分類（閾値 ±0.2）。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。
  - score_regime(conn, target_date, api_key=None) を公開。APIキー未設定時は ValueError を送出。

- リサーチ / ファクター (src/kabusys/research/*.py)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 不在/0 は None）。
    - DuckDB を用いた SQL ベースの実装で、外部 API へのアクセスは行わない設計。
  - feature_exploration.py:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する高速クエリ実装。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算（有効レコード 3 未満で None）。
    - rank: 同順位は平均ランクを取るランク化実装（丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - すべて標準ライブラリと DuckDB のみで実装（pandas 非依存）。

- データプラットフォーム (src/kabusys/data/*.py)
  - calendar_management.py:
    - JPX カレンダー（market_calendar テーブル）を扱うユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。DB にデータが無い場合は曜日ベースでフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル、健全性チェック、jquants_client 経由）。
  - pipeline.py / etl.py:
    - ETLResult データクラスを定義し、ETL 処理結果の集約（取得数・保存数・品質問題・エラー）を表現。
    - jquants_client と quality モジュールを用いる差分取得・保存・品質チェックの想定（詳細実装は jquants_client 等に依存）。
    - ETL の設計方針（差分更新・backfill・品質チェックは致命的エラーでも収集継続）を明記。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）。

### セキュリティ (Security)
- なし

### 備考 / 実装上の注意
- OpenAI 利用:
  - news_nlp と regime_detector は OpenAI API の JSON mode（gpt-4o-mini）を使用するため、OPENAI_API_KEY の設定が必須（関数呼び出し時に引数で注入可能）。
  - API 呼び出しはテスト容易性のためモック差し替えポイント（_call_openai_api）を持つ。
  - API エラーに対してはフェイルセーフ（スコア 0.0 等）で継続する方針を採用。
- DuckDB 前提:
  - 多くの処理は DuckDB 接続を前提とした SQL 実装となっており、テーブル名（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）に依存する。
- ルックアヘッドバイアス対策:
  - 日付処理（target_date）は外部参照（datetime.today() 等）を避け、与えられた target_date 未満／以前のデータのみを使う設計。
- ログ出力:
  - 主要処理で logger を利用し、API 失敗・データ不足・ROLLBACK 失敗等で適切に警告/情報ログを出力する。

---

今後のリリース案（例）
- 0.2.0: 発注周り（execution）・戦略モジュール（strategy）・監視（monitoring）の実装、テストカバレッジ追加、ドキュメント整備。
- 1.0.0: 安定版リリース（破壊的変更のない API と十分なテスト・運用機能の搭載）。

（この CHANGELOG はソースコードの内容から推測して作成しています。詳細や追加の変更点は実際のコミット履歴・ISSUE を参照してください。）