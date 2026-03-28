Keep a Changelog 準拠 — 変更履歴 (日本語)
====================================

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠します。

Unreleased
----------
- なし

0.1.0 - 2026-03-28
------------------
Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージルート:
    - src/kabusys/__init__.py: バージョン情報（0.1.0）と公開サブパッケージ定義（data, strategy, execution, monitoring）。
  - 設定・環境変数管理:
    - src/kabusys/config.py:
      - .env/.env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索して決定）。
      - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - export KEY=... 形式、クォート・エスケープ、コメント扱いなどを考慮した独自パーサ実装。
      - .env.local は .env を上書きする扱い（ただし OS 環境変数は保護）。
      - Settings クラス提供（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等のプロパティ）とバリデーション（KABUSYS_ENV、LOG_LEVEL の許容値チェック）。
  - AI（自然言語処理）機能:
    - src/kabusys/ai/news_nlp.py:
      - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でバッチ評価して ai_scores テーブルへ書き込む処理を実装。
      - 時間ウィンドウ計算（JST ベース→UTC 比較用変換）、記事トリム（件数・文字数制限）、バッチサイズ（最大 20 銘柄）をサポート。
      - リトライ（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ、レスポンスの厳密なバリデーション、スコア ±1.0 のクリップ、部分成功時に既存スコアを保護する idempotent 書き込みロジックを実装。
      - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等的に書き込む機能を実装。
      - マクロキーワードで raw_news をフィルタし、OpenAI で macro_sentiment を評価（記事がない場合は LLM 呼び出しを行わず 0.0 を使用）。
      - API 呼び出しのリトライ/バックオフ、500 系の扱い、JSON パース失敗時のフェイルセーフ（0.0 へフォールバック）を実装。
  - データ（Data Platform）:
    - src/kabusys/data/calendar_management.py:
      - market_calendar テーブルを用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
      - DB にデータがない場合は曜日ベースでフォールバックする設計、最大探索日数を設定して無限ループ回避、バックフィル・健全性チェックを実装。
      - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新する夜間バッチ処理（バックフィルとサニティチェックを含む）。
    - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py:
      - ETL パイプラインの基盤（差分取得・保存・品質チェックの方針）。
      - ETLResult データクラスを公開（ETL 結果の集約、品質問題・エラー一覧、has_errors/has_quality_errors 等のユーティリティ）。
      - DuckDB を用いた最大日付取得などのヘルパーを実装。
    - src/kabusys/data/__init__.py, src/kabusys/data/etl.py の公開 API 整備（ETLResult の再エクスポート）。
  - リサーチ / ファクター:
    - src/kabusys/research/factor_research.py:
      - Momentum, Value, Volatility, Liquidity 等のファクター計算（calc_momentum, calc_value, calc_volatility）。
      - DuckDB 内の prices_daily / raw_financials を用いた SQL + Python 実装、データ不足時の None 扱い、結果は (date, code) キー辞書リストで返却。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
      - 外部依存を避け標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py:
      - 主要関数の再エクスポート（calc_momentum 等、zscore_normalize の再公開）。
  - 設計上の注意点（全体）:
    - ルックアヘッドバイアス防止のため各モジュールは datetime.today() / date.today() を直接参照しない（score_* / calc_* は target_date を明示的に受け取る）。
    - DB 書き込みは冪等性を重視（DELETE→INSERT / ON CONFLICT 等）し、部分失敗時に既存データを保護する挙動を多用。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なパース・バリデーションを実装。
    - テスト容易性のため API 呼び出し部分（_call_openai_api）を差し替え可能に設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キー未設定時に明示的な ValueError を送出することで、キー漏洩につながる挙動や不明瞭な失敗を避ける設計。
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時の安全策）。

注記（実装上の既知点）
- OpenAI との連携は gpt-4o-mini を前提にした JSON Mode を想定しているため、異なる API 仕様や将来の SDK 変更により調整が必要になる可能性があります。
- DuckDB の executemany に関する互換性（空リスト不可など）を考慮した実装が随所にあるため、DuckDB のバージョンに依存する挙動に注意してください。
- 一部モジュールは外部サービス（J-Quants, kabuステーション, Slack 等）との統合が前提になっており、実行環境側で対応する環境変数や API クライアント設定が必要です。

--- 
この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に合わせて適宜編集してください。