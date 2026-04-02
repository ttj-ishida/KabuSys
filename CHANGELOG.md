CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
このファイルはコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし（初回リリース候補）

[0.1.0] - 2026-04-02
-------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、公開モジュール: data, research, ai, execution, strategy, monitoring（__init__.py によるエクスポート）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境変数/設定管理機能（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能と読み込み優先順位 (OS 環境変数 > .env.local > .env) を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env のパースはコメント、export 形式、引用符・エスケープ対応、インラインコメントの取り扱いなどを実装。
  - 既存 OS 環境変数を保護する protected パラメータを利用して .env.local 上書き時の安全性を高める。
  - 設定取得用 Settings クラスを提供（J-Quants、kabuステーション、Slack、DB パス、監視閾値、環境判定、ログレベルなどのプロパティを用意）。
  - 必須設定取得時に未設定だと ValueError を送出する _require ユーティリティ。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI (gpt-4o-mini) の JSON Mode によるバッチスコアリング機能を実装。
    - バッチ/チャンク処理（デフォルト最大20銘柄/チャンク）、1銘柄あたり記事数と文字数の上限制御、レスポンスの厳密なバリデーション、スコア ±1.0 にクリップ。
    - 再試行戦略: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでのリトライ。その他エラーはスキップするフェイルセーフ設計。
    - テスト容易性: OpenAI 呼び出し部は差し替え可能（ユニットテストで patch 可能）。
    - calc_news_window 関数でニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC で計算。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロ経済ニュースの LLM センチメント (重み 30%) を合成して日次で 'bull'/'neutral'/'bear' を判定し market_regime テーブルへ冪等書き込み。
    - MA 計算、マクロ記事フィルタ（キーワードベース）、OpenAI 呼び出し、リトライ/フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - レスポンス JSON パースや API エラーに対する詳細なログとリトライ挙動を備える。
    - 設計上、datetime.today()/date.today() を直接参照せずルックアヘッドバイアスを防止。

- データプラットフォーム関連（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar の DB ベースの営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベース（平日のみ営業）でフォールバックする堅牢な設計。
    - calendar_update_job により J-Quants から差分取得し冪等に保存、バックフィル/健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を定義（取得件数、保存件数、品質チェック結果、エラー一覧等を格納）。
    - 差分取得、バックフィル、品質チェック、idempotent 保存（jquants_client の save_* を利用）等の方針を実装（実装の骨子）。
  - ETL 公開インターフェース（src/kabusys/data/etl.py）
    - pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER、ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金/出来高比）等の計算関数を実装。
    - DuckDB に対する SQL ベースの実装で、prices_daily/raw_financials のみを参照する安全設計。
    - 不足データ時の None 処理やログ出力を明示。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（calc_ic: Spearman の ρ によるランク相関）、ランク付けユーティリティ、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

Changed
- （初回リリース）コード設計上の重要な方針を明示
  - ルックアヘッドバイアス回避のため、日付参照を外部引数化（date.today() を直接参照しない）。
  - OpenAI 呼び出しを各モジュール内で独立実装し、モジュール間のプライベート関数共有を避けテストしやすく設計。

Fixed
- N/A（初回リリースとして既存実装の要約）

Deprecated
- なし

Removed
- なし

Security
- .env 読み込み時に既存 OS 環境変数を protected として扱い、.env.local による上書きでも OS 環境変数が保護される仕組みを導入。
- OpenAI API キー / J-Quants トークン / Slack トークンなど必須機密情報は Settings 経由で取得・未設定時は明示的なエラーを発生させる。

Notes / Known limitations
- 実行には外部 API キー（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN 等）や kabu ステーションの認証情報が必要。Settings のプロパティにより取得する。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提となる。
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を期待した実装。実環境では API レスポンス形式の差分に注意が必要。
- 一部 DuckDB バインドの互換性（executemany と空リスト）を考慮したガードを実装済み。

作者
- コードベースの内容から推測して作成した変更履歴です。実際のコミット履歴やリリース日時に合わせて調整してください。