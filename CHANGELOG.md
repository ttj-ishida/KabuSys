# Changelog

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に従い、セマンティックバージョニングを想定しています。

最新の変更は常に一番上に記載します。

## [0.1.0] - 2026-03-31

初期リリース。本リポジトリに含まれる主要機能・モジュールを追加しています。

### 追加 (Added)
- パッケージのエントリポイント
  - kabusys パッケージ初期化（src/kabusys/__init__.py）およびバージョン定義（__version__ = "0.1.0"）。

- 環境設定・自動 .env ロード (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パース機能を実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート文字列のエスケープ処理に対応。
    - インラインコメントの取り扱いを考慮（クォート有無で挙動を区別）。
  - .env/.env.local の上書きルール:
    - OS 環境変数を保護する protected キーセットを導入。
    - .env を先に読み込み、.env.local で上書き（override=True）する優先順位。
  - Settings クラスを追加してアプリケーション設定をプロパティとして提供:
    - J-Quants / kabu ステーション / Slack / DB パス等の必須・既定値設定。
    - env（development/paper_trading/live）や log_level のバリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
    - 必須環境変数未設定時は意味のある例外メッセージを発行。

- AI モジュール: ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ計算（JST: 前日 15:00 ～ 当日 08:30）を提供する calc_news_window 関数を実装。
  - バッチ処理（_BATCH_SIZE=20）、1銘柄あたり最大記事数・最大文字数のトリム (_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK) を実装。
  - OpenAI 呼び出しは JSON Mode（厳密な JSON を期待）で行い、レスポンスのバリデーションと安全なパースを実装。
  - 失敗耐性:
    - 429、ネットワーク断、タイムアウト、5xx に対するエクスポネンシャルバックオフでのリトライ処理。
    - API 失敗やパース失敗時はそのチャンクをスキップし、全体処理は継続（フェイルセーフ）。
  - DuckDB への書き込みは部分失敗時の安全を考慮して、取得済みコードのみ DELETE → INSERT で置換（冪等性を確保）。
  - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能。

- AI モジュール: 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み付きで合成し、market_regime テーブルへ日次スコアを書き込む機能を実装。
  - 設定:
    - ma 重み 70%、マクロ重み 30%（スケーリング含む）。
    - bull/bear 判定閾値（±0.2）や最大記事数等の定数を定義。
  - DuckDB クエリにてルックアヘッドバイアス対策（target_date 未満のみ参照）を徹底。
  - OpenAI 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックして処理継続。
  - DB 書き込みはトランザクション内で DELETE→INSERT を行い冪等性を担保。
  - テスト容易性: _call_openai_api を差し替え可能。

- リサーチモジュール（src/kabusys/research/*.py）
  - factor_research.py:
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER, ROE）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB で SQL を用いて効率的に計算し、(date, code) をキーとする dict のリストを返す。
    - データ不足時の扱い（None）やログ出力を実装。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）、IC（calc_ic: スピアマンランク相関）、ランキング変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - Pandas に依存せず標準ライブラリ + DuckDB で実装。
  - research パッケージ __all__ で主要関数を再エクスポート。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management.py:
    - JPX カレンダー管理と営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job を実装し、J-Quants API 経由で市場カレンダーを差分取得して保存する処理を提供（バックフィル・健全性チェック含む）。
    - DB がまばらでも一貫したフォールバック（DB優先、未登録日は曜日ベース）を実現。
  - pipeline.py:
    - ETL パイプラインの基盤を実装。差分取得、保存、品質チェックのフロー想定をコメントで規定。
    - ETLResult データクラスを実装し、取得件数・保存件数・品質問題・エラーなどを集約して返す。
    - DuckDB の存在チェックや最大日付取得のユーティリティを実装。
  - etl.py:
    - pipeline.ETLResult を外部公開（再エクスポート）。

- 共通事項
  - DuckDB を主要なデータストアとして想定（多くの関数が DuckDB の接続型を引数に取る）。
  - すべての日時処理は date / naive datetime で統一し、タイムゾーン混入を防止する設計。
  - ルックアヘッドバイアス防止の観点から datetime.today()/date.today() を各処理内で参照しない実装方針を明記。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キー（OPENAI_API_KEY）や各種トークンは環境変数で管理。Settings クラスは必須トークン未設定時に ValueError を送出して明示的に扱う設計。
- .env ロード時、既存の OS 環境変数は保護される（上書き防止）ため、意図しない環境漏洩を抑止。

---

注:
- 本 CHANGELOG はソースコードの内容から推測して作成されています。実際のリリースノートや履歴の記載方針に合わせて適宜修正してください。