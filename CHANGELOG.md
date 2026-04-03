# CHANGELOG

すべての重要な変更点を記録します。このファイルは Keep a Changelog の形式に準拠します。  
変更履歴はセマンティックバージョニングに従います。

- リンク: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買システム（KabuSys）の基盤機能をまとめて公開します。以下はコードベースから推測してまとめた主な追加・設計方針・注意点です。

### Added
- パッケージ基本情報
  - パッケージ名 / 説明: KabuSys - 日本株自動売買システム
  - バージョン定義: `__version__ = "0.1.0"`

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロードする機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）を無視
    - export で始まる行を許容（`export KEY=val`）
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - 非クォート時のインラインコメント処理（直前が空白/タブの場合のみ）
  - `.env` / `.env.local` の読み込み優先度を考慮し、既存 OS 環境変数を保護するための protected set をサポート。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - J-Quants / kabu ステーション / LINE API トークン、データベースパス（DuckDB / SQLite）、監視用 PID/KILL フラグ、閾値、環境（development/paper_trading/live）、ログレベル等
  - 必須設定未指定時は明確な `ValueError` を送出する `_require` 実装。
  - `env` / `log_level` の入力値検証（ホワイトリスト）を実装。

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出。
    - JST の「前日15:00〜当日08:30」を対象とするウィンドウ計算（UTC 変換済み）を実装（calc_news_window）。
    - 1銘柄あたりの記事数／文字数の上限（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）を設け、プロンプト肥大化を防止。
    - 最大 20 銘柄ずつのバッチ送信（_BATCH_SIZE）。
    - API 呼び出しに対し 429 / ネットワークエラー / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - OpenAI の JSON モードを使い、レスポンスのバリデーション（results キー、型チェック、既知コードのみ採用、数値チェック）とスコアの ±1.0 クリップ。
    - DuckDB への書き込みは、部分失敗時に既存データを守るため書き込み対象コードのみ削除→挿入する冪等処理（BEGIN / DELETE(s) / INSERT(s) / COMMIT）。
    - テスト容易性のため、内部の OpenAI 呼び出し関数は `kabusys.ai.news_nlp._call_openai_api` をパッチ可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはニュースタイトルをマクロ関連キーワードでフィルタして取得し、OpenAI（gpt-4o-mini）で JSON 出力（{"macro_sentiment": float}）を要求、スコアは -1.0〜1.0 にクリップ。
    - API 呼び出し失敗時は macro_sentiment = 0.0 としてフェイルセーフに継続。
    - DuckDB への書き込みは冪等化（DELETE→INSERT をトランザクション内で実行）。OpenAI 呼び出し部分も patchable な `_call_openai_api` を別実装で用意し、news_nlp と明示的に分離。

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。データ不足時は None を返す。
    - Volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率など。
    - Value: latest raw_financials（report_date <= target_date）と target_date の株価から PER / ROE を計算。EPS が 0/欠損のときは None。
    - DuckDB を用いた SQL 主導の実装。外部 API/発注 API にはアクセスしない設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン calc_forward_returns（複数ホライズンを同時取得、範囲は max_horizon の 2 倍カレンダー日でスキャン）。
    - IC（Information Coefficient）計算：Spearman ランク相関（ties は平均ランクで処理）。
    - rank / factor_summary：外部ライブラリに依存せず標準ライブラリのみで統計量を算出（count/mean/std/min/max/median）。

  - パッケージ公開用の __all__ を整備し、主要関数を明示的に公開（研究用 API 整備）。

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを参照する営業日判定ロジック：
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar 未取得日は曜日ベース（土日非営業）でフォールバックし、一貫性を保つ実装。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック）。
    - 最大探索日数やバックフィル日数、lookahead 等に安全装置を配置。

  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー情報等を保持、to_dict を提供）。
    - pipeline モジュールは差分更新、idempotent 保存、品質チェック（quality モジュール）を想定した設計（詳細実装は pipeline に依存）。
    - data/etl.py で ETLResult を再エクスポート。

- インフラ / 共通
  - DuckDB を主要なローカル分析 DB として利用。
  - OpenAI モデル: gpt-4o-mini を明示的に使用。
  - 各種処理においてルックアヘッドバイアスを避けるため、datetime.today()/date.today() を参照しない方針を徹底（一部ジョブで日付計算は引数 target_date を用いる）。
  - ロギングと WARN/INFO/DEBUG で詳細な実行ログを記録する設計。
  - テストしやすい patch ポイント（OpenAI 呼び出しなど）を用意。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- OpenAI / 各種 API キーは環境変数で管理（`OPENAI_API_KEY` など）。必須キー未指定時は明確な例外を投げることで誤った公開を抑制。

### Notes / Implementation details / 設計上の注意点
- .env の自動読み込みはパッケージ内からプロジェクトルートを検索して行うため、配布後の挙動やテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って無効化することを推奨します。
- OpenAI レスポンスのパースは冗長テキスト混入ケースにも対応（最外側の {} を抽出してパースを試みる等）。
- API 呼び出し失敗時はフェイルセーフで処理を継続し、部分的なデータ取得に留める設計（完全停止よりも既存データを保護）。
- DuckDB に対する executemany の空リストバインド制約を考慮し、空チェックを挟んでから実行する実装になっています。
- news_nlp / regime_detector 両方で内部の OpenAI 呼び出しは別々に実装しており、モジュール結合を避ける設計。

---

今後のリリースでは以下のような項目を想定しています（要望・課題の候補）:
- 監視/実行モジュール（execution / monitoring）や発注ロジックの追加・安全性向上（実売買に関わるテストカバレッジ強化）
- より柔軟なモデル選択やロギングの改善、メトリクス出力の追加
- J-Quants / kabu API クライアントの詳細実装と連携テスト
- 品質チェック（quality module）の具体実装とルール強化

（この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のプロジェクト運用に合わせて適宜修正・追記してください。）