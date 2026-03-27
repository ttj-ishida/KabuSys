CHANGELOG
=========

すべての変更点は「Keep a Changelog」形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初回リリース。
- パッケージメタ:
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - パブリックサブパッケージ: data, strategy, execution, monitoring を公開。

- 環境設定管理（src/kabusys/config.py）:
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート検出は .git または pyproject.toml を使用）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - 環境変数の保護（既存 OS 環境変数の上書き防止）対応と override オプション。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベルの検証等）。
  - 必須環境変数未設定時は ValueError を送出する _require 実装。

- AI 関連（src/kabusys/ai/）:
  - ニュース NLP（src/kabusys/ai/news_nlp.py）:
    - raw_news を集約して OpenAI（gpt-4o-mini）に送り銘柄ごとのセンチメント ai_score を算出。
    - JST ベースのニュースウィンドウ算出（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大20銘柄 / チャンク）、1銘柄あたりの最大記事数および最大文字数でトリム。
    - OpenAI 呼び出しはリトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。
    - JSON Mode のレスポンス検証ロジックを実装（余分な前後テキストの補正、results 配列検証、未知コード除外、数値チェック、±1.0 でクリップ）。
    - DB への書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT の冪等更新。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で market_regime を判定・保存。
    - prices_daily / raw_news を参照して ma200_ratio を計算、マクロ記事はキーワードでフィルタして OpenAI に送信。
    - OpenAI 呼び出しはリトライ／フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - レジームスコアはクリップされ、しきい値に基づき 'bull' / 'neutral' / 'bear' ラベルを割当てる。
    - DB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等化。失敗時は ROLLBACK を試行し例外を上位に伝播。

- データプラットフォーム（src/kabusys/data/）:
  - カレンダー管理（src/kabusys/data/calendar_management.py）:
    - market_calendar テーブルを用いた営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 未取得時は曜日ベースのフォールバック（週末を非営業日扱い）。
    - next/prev_trading_day は最大探索日数を設定して無限ループを防止。
    - calendar_update_job により J-Quants から差分取得 → market_calendar への冪等保存（バックフィル、健全性チェック含む）。
    - J-Quants クライアント呼び出しを jquants_client モジュールと連携。

  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）:
    - ETLResult データクラスを公開（src/kabusys/data/etl.py 経由で再エクスポート）。
    - 差分取得、保存（idempotent）、品質チェックの設計に対応するユーティリティを実装。
    - テーブル最大日付取得、テーブル存在確認などの内部ユーティリティを提供。
    - デフォルトのバックフィル日数・カレンダー先読み等を定義。

  - jquants_client / quality 等のモジュールとの連携を想定した設計（実装は依存モジュール側）。

- リサーチ（src/kabusys/research/）:
  - factor_research（src/kabusys/research/factor_research.py）:
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離率）。
    - Volatility / Liquidity: atr_20（20日 ATR）/ atr_pct / avg_turnover / volume_ratio。
    - Value: per（株価/EPS）, roe（raw_financials から取得）。
    - DuckDB を用いた SQL ベースの計算。データ不足時は None を返す挙動。
    - 返却フォーマットは date, code を含む dict のリスト。

  - feature_exploration（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算: calc_forward_returns（horizons デフォルト [1,5,21]）— LEAD を用いた単一クエリ取得。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランク変換で算出、有効レコードが 3 未満は None）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク、丸め処理で ties 検出の安定化）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）。
    - kabusys.data.stats.zscore_normalize を再エクスポートし利用可能に。

- 汎用実装・設計上の方針（プロジェクト全体）:
  - DuckDB を主要なローカル分析 DB として使用。
  - OpenAI（gpt-4o-mini）を JSON mode で利用、レスポンスバリデーションを厳密に実施。
  - API 呼び出しは明示的にリトライ（指数バックオフ）とフェイルセーフを実装。非致命的失敗時は処理継続（例: スコア取得失敗でスキップ）。
  - いずれの処理も datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス対策）。target_date ベースで計算。
  - DB 書き込みは冪等性を考慮（DELETE→INSERT や ON CONFLICT を想定）し、失敗時は ROLLBACK を試行。
  - ロギングを広範に配置し、警告・情報ログで運用上の事象を可視化。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 運用上の留意点
- OpenAI API キーは環境変数 OPENAI_API_KEY または各関数の api_key 引数で指定。未設定時は例外を投げる設計。
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされる（配布後の安全性）。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、空チェックを行った上で executemany を呼び出す実装になっている。
- 性能・コスト面では OpenAI へのバッチサイズ・記事トリム等で調整可能（定数はソース内部で調整可能）。

今後の予定（想定）
- strategy / execution / monitoring 周りの具体的な売買ロジック・発注・監視機能の実装。
- テストカバレッジと CI の整備（OpenAI 呼び出しのモックや DB フェイクを含む）。
- jquants_client や kabu ステーション連携の実装・強化。

--- 
この CHANGELOG はコード内のドキュメント、関数シグネチャ、定数・ログメッセージ等から推定して作成しています。必要があれば項目の追加・修正を行います。