# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
本ファイルは Keep a Changelog の形式に準拠しています。  
安定したバージョンはセマンティックバージョニングを採用します。

最新: Unreleased

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-04
初回公開リリース。

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール群: data, strategy, execution, monitoring を __all__ でエクスポート

- 環境設定 (kabusys.config)
  - .env/.env.local ファイルまたは OS 環境変数から設定を自動読み込みする機能を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、__file__ を起点に探索（CWD 非依存）
    - .env パーサは export KEY=val、クォート（' "）・エスケープ、行末コメントなどに対応
    - .env 読み込み時、override と protected（OS 環境変数セット）を扱う
  - Settings クラスを提供（settings インスタンス経由で利用）
    - J-Quants / kabuAPI / LINE / DB / 監視 / システム設定のプロパティを用意
    - 必須環境変数取得用の _require() を実装（未設定時は ValueError）
    - バリデーション:
      - KABUSYS_ENV は development / paper_trading / live のいずれかでなければエラー
      - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容
    - 各種デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）を定義
    - kill_flag_clear_on_start 等のフラグ、リソース閾値（CPU/MEM/DISK）のデフォルトも定義

- ニュースNLP（kabusys.ai.news_nlp）
  - 関数: score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でセンチメントを評価
    - calc_news_window(target_date) により対象ニュース時間ウィンドウ（前日15:00 JST〜当日08:30 JST）を計算
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - レスポンスは JSON Mode を期待し、厳密な検証 (_validate_and_extract) を実施
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ（_MAX_RETRIES/_RETRY_BASE_SECONDS）
    - 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）
    - 成功したスコアのみ ai_scores テーブルに置換的に書き込み（DELETE → INSERT、部分失敗時に既存データを保護）
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出

  - 内部設計上の注意点:
    - datetime.today()/date.today() を参照せず、target_date のみで判定（ルックアヘッドバイアス回避）
    - テスト用に _call_openai_api を patch 可能（モジュール間で共有しない独立実装）

- レジーム判定（kabusys.ai.regime_detector）
  - 関数: score_regime(conn, target_date, api_key=None)
    - ETF 1321（日経225連動）に基づく 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定
    - ma200_ratio 計算は target_date 未満データのみ使用（ルックアヘッド回避）
    - マクロニュースの抽出はマクロキーワード一覧に基づくフィルタ（最大 20 記事）
    - LLM 呼び出し（gpt-4o-mini）で JSON 形式の {"macro_sentiment": float} を期待。API 失敗時は 0.0 をフォールバック
    - レジームスコアはクリップされ、閾値によりラベル化
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API キー未設定時は ValueError

  - 内部特性:
    - リトライ / エラーハンドリング（RateLimit/APIConnection/APITimeout/APIError に応じた挙動）
    - OpenAI 呼び出しは news_nlp と独立して実装（モジュール結合を避ける）

- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを基に営業日判定・前後営業日取得・期間内営業日列挙・SQ 判定を提供
    - DB にデータがない場合は曜日ベース（平日のみ営業）でフォールバック
    - next_trading_day / prev_trading_day は最大探索範囲 (_MAX_SEARCH_DAYS) を設け、過度なループを防止
    - calendar_update_job(conn, lookahead_days) により J-Quants API から差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）
    - バックフィルや健全性チェック（将来日付の異常検出）を実装

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）
      - ETL 実行結果（取得数・保存数・品質問題・エラー等）を保持し、辞書化可能（to_dict）
      - has_errors / has_quality_errors のヘルパーを提供
    - pipeline モジュールは差分更新、保存（idempotent）、品質チェックの設計方針を定義（詳細は pipeline.py）
    - _get_max_date / _table_exists 等のユーティリティを実装（DuckDB 向け）

- 研究・因子 (kabusys.research)
  - factor_research: calc_momentum, calc_value, calc_volatility を実装
    - Momentum: mom_1m/mom_3m/mom_6m、200 日 MA の乖離（ma200_dev）
    - Volatility/Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、avg_turnover、volume_ratio
    - Value: PER（price/EPS）、ROE（raw_financials から最新財務を取得）を提供
    - 入力は DuckDB の prices_daily / raw_financials のみ（外部 API にアクセスしない）
    - データ不足時は None を返す設計
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算
    - rank: 同順位は平均ランクで処理、丸め誤差対策として round(v,12) を使用
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）
    - pandas 等を使わず標準ライブラリで実装

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### 既知の注意点 / 実装上の設計判断
- OpenAI への呼び出しは JSON Mode を期待しているが、実運用では LLM が厳密な JSON を返さない場合があるため、レスポンスパース時に最外の {} を抽出する復元処理を行っている（それでも失敗する場合はスコアをスキップ）
- API のエラー処理はフェイルセーフを重視し、致命的な例外を極力抑えて処理継続する設計（部分失敗を許容し、失敗したチャンク/銘柄のみをスキップ）
- DuckDB の executemany に空リストを渡せないバージョン互換性を考慮して、空チェックを挟んでいる
- 時刻取り扱いは UTC naive を基本にし、calc_news_window 等で JST ↔ UTC の変換を内部で行っている（全て date/datetime オブジェクトで扱う）

### セキュリティ (Security)
- 初回リリースのため該当なし。API キー等の資格情報は環境変数（.env）経由での管理を想定

---

作業メモ・開発者向け:
- 環境変数の自動ロード挙動はテスト時に混乱を招くため、ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化することを推奨します。
- OpenAI 呼び出しはテストでの差し替えを想定して _call_openai_api を patch することでモック化できます。

（以上）