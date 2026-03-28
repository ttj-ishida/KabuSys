# Changelog

すべての注目すべき変更をこのファイルで管理します。  
形式は「Keep a Changelog」に準拠しています。  

最新版: 0.1.0（初回リリース）

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回公開リリース。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- パッケージ基礎
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。
  - モジュール公開 API を __all__ で宣言（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml）。
  - .env / .env.local の読み込み順と上書きポリシーを実装（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env のパースを堅牢化：
    - export KEY=val 形式対応
    - シングル・ダブルクォート内のバックスラッシュエスケープ処理対応
    - 行末コメント（#）の扱いを文脈依存で処理
  - 必須環境変数の取得関数 _require と、Settings クラスによる集中管理を提供。
  - Settings で J-Quants / kabuステーション / Slack / DB パス / 環境(env) / ログレベルのプロパティを提供し、値検証（有効な env / LOG_LEVEL のチェック）を実施。
  - デフォルト DB パス（DuckDB / SQLite）の展開（Path.expanduser）を実装。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
  - ニュース対象ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を計算する calc_news_window を実装。
  - バッチ処理（最大 20 銘柄/回）、記事数・文字数上限（記事数: 10 件、文字数: 3000 文字）によるプロンプトトリミングを実装。
  - レート制限(429)・ネットワーク断・タイムアウト・5xx に対して指数バックオフによるリトライを実装（デフォルト上限）。
  - OpenAI レスポンスの堅牢なバリデーション／パース（前後の余計なテキストから最外部 JSON を抽出する処理含む）を実装。
  - スコアは ±1.0 にクリップ。部分成功時にも既存の ai_scores を保護するため書き込みは対象コードのみ DELETE → INSERT を行う（冪等性確保）。
  - テストしやすさを考慮し、OpenAI 呼び出しを内部関数で分離しモック可能に設計。

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（Nikkei 225 連動型）200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を生成。
  - prices_daily（1321）から MA200 乖離を計算する _calc_ma200_ratio、マクロ記事抽出、LLM 呼び出し（gpt-4o-mini / JSON Mode）による macro_sentiment 評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
  - API エラー時は macro_sentiment = 0.0 にフォールバックするフェイルセーフを採用。
  - OpenAI 呼び出しは独立実装で、news_nlp とはモジュール結合しない設計（テスト容易性・分離性を重視）。

- データプラットフォーム（src/kabusys/data）
  - calendar_management.py
    - JPX カレンダーの管理機能を実装（market_calendar テーブルの参照/更新）。
    - 営業日判定ユーティリティ群を提供：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーが無い/未登録日の場合は曜日ベース（平日）でフォールバックする一貫した動作を実装。
    - calendar_update_job により J-Quants からカレンダー差分を取得して保存する夜間バッチ処理を実装（バックフィル・健全性チェック含む）。
  - pipeline.py / etl.py
    - ETL の高レベルインターフェースと ETLResult データクラスを実装。
    - 差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュール連携）を想定した設計。
    - ETLResult には品質チェック結果やエラー一覧を保持し、辞書化（監査ログ用）する to_dict を提供。
    - テスト性・互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティを提供。

- リサーチ／ファクター（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、出来高指標）、Value（PER、ROE）の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの実装で、prices_daily / raw_financials のみに依存。
    - データ不足時の None ハンドリングやロギングを実施。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで完結する実装。
  - research/__init__.py で主要関数群を再エクスポート（研究用 API を整理）。

- その他
  - ai/__init__.py に score_news を公開エントリポイントとして追加。
  - data/etl.py で ETLResult を再エクスポート。
  - docstring や関数コメントに設計方針（ルックアヘッドバイアス防止、フェイルセーフ、冪等性など）を明記。

### 変更 (Changed)
- なし（初回リリースのため既存コード差分なし）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- OpenAI API キーは引数で注入でき、未指定時は環境変数 OPENAI_API_KEY を参照する実装。キーの取り扱い（ログ等に出力しない）については使用側で注意すること。

### 注意事項 / 既知の制限
- DuckDB バージョン依存の制約（executemany に空リストを渡せない等）に配慮した実装になっています。運用環境の DuckDB バージョンに依存する箇所がある点に注意してください。
- OpenAI とのやり取りは JSON Mode を前提としていますが、稀に余計なテキストが混入する想定で復元ロジックを組んでいます。レスポンス仕様の変更があった場合はパースロジックの見直しが必要です。
- news_nlp / regime_detector は API 失敗時にスコアを 0.0 とするフェイルセーフを採用しており、完全性よりも可用性を優先しています。運用方針に応じて例外伝播に変更可能です。

---

（この CHANGELOG はソースコードの実装内容および docstring から推測して作成しています。実際のリリースノート作成時は変更差分や Git のコミット履歴に基づく追記・修正を行ってください。）