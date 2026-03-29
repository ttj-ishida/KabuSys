CHANGELOG
=========
すべての注目すべき変更はこのファイルに記録します。本ファイルは「Keep a Changelog」の慣例に従っています。

フォーマット:
- Unreleased: 次のリリースに向けた未反映の変更
- 各リリース: 日付付きで Added / Changed / Fixed / Security 等に分類

Unreleased
----------
（なし）

0.1.0 - 2026-03-29
-----------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を定義
    - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ に設定

- 設定・環境変数管理
  - src/kabusys/config.py を追加
    - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）
    - .env パーサ実装（export 語彙、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）
    - OS 環境変数を保護する protected オプション、上書き制御（KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化）
    - 必須環境変数取得ユーティリティ _require と Settings クラスを提供
    - 主要設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH
      - KABUSYS_ENV（development/paper_trading/live のバリデーション）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
      - is_live / is_paper / is_dev の判定ヘルパ

- AI モジュール（OpenAI を用いた NLP）
  - src/kabusys/ai/news_nlp.py: ニュースセンチメントスコアリング
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して ai_scores に書き込み
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の実装 calc_news_window）
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数・最大文字数制限
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライ
    - レスポンスの厳格なバリデーション（JSON 抽出・results 構造・既知コード・数値チェック）
    - スコア ±1.0 でクリップ、部分成功時の DB 保護のため DELETE→INSERT の置換処理
    - テスト容易性: _call_openai_api をパッチ差し替え可能

  - src/kabusys/ai/regime_detector.py: 市場レジーム判定
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウから抽出
    - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得、API 障害時はフェイルセーフにより 0.0 を採用
    - レジームスコア合成後に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API リトライ・ログ・安全な例外取扱いを実装
    - テスト容易性: _call_openai_api を差し替え可能

- データ処理・ETL
  - src/kabusys/data/pipeline.py: ETL パイプラインの基本骨格
    - ETLResult dataclass（取得件数・保存件数・品質問題・エラー一覧・ユーティリティ）を導入
    - 差分取得・バックフィル・品質チェック等の設計方針を実装
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装
    - エラー・品質問題を収集して呼び出し元に知らせる設計（Fail-Fast ではない）

  - src/kabusys/data/etl.py: ETLResult の再エクスポート

  - src/kabusys/data/calendar_management.py: マーケットカレンダー管理
    - 営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない場合は曜日ベース（土日休み）でフォールバック
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、先読み、健全性チェック）
    - 最大探索日数やバックフィルなどの安全ガードを実装

- リサーチ／ファクター計算
  - src/kabusys/research/factor_research.py: ファクター計算機能
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（必要行数チェック）
    - calc_value: PER / ROE（raw_financials の最新報告を使用）
    - DuckDB SQL を活用した効率的な計算（窓関数等）

  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンを一回のクエリで計算
    - calc_ic: スピアマンランク相関（ランク付け/同位データの平均ランク処理）
    - rank: 同順位は平均ランク、丸め処理で ties 検出の安定化
    - factor_summary: count/mean/std/min/max/median の統計サマリー
    - research パッケージの __init__ で主要関数を公開

- 共通設計方針・品質
  - DuckDB をデータストアとして採用（DuckDB 用の互換性/制約に対応）
  - ルックアヘッドバイアス回避: 各処理は datetime.today()/date.today() を直接参照しない（target_date ベース）
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定の設計）
  - OpenAI 呼び出しでの安全対策（再試行・5xx 判定・レスポンス検証・フェイルセーフ）
  - ロギングを多用し失敗原因やフォールバックを明示
  - テスト容易性を考慮した設計（内部 API 呼び出しのパッチ差し替えポイント等）
  - .env の読み込み順序: OS 環境 > .env.local > .env

Changed
- （このリリースは初回リリースのため該当なし）

Fixed
- （このリリースは初回リリースのため該当なし）

Security
- 環境変数の必須チェックは Settings._require にて ValueError を投げることで誤設定を早期通知
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト/一時運用向け）

Notes / 開発者向けメモ
- OpenAI の使用には環境変数 OPENAI_API_KEY の設定が必須（関数引数からも注入可能）
- news_nlp と regime_detector は gpt-4o-mini を想定してJSON Mode で応答を受け取りパースする
- DuckDB の executemany に対するバージョン依存の注意点（空リスト渡しを避ける実装を採用）
- J-Quants 関連クライアント（jquants_client）は data モジュールから参照されるが、実装の詳細は別モジュール（外部）に依存

今後の予定（例）
- strategy / execution / monitoring の具体実装（現在はパッケージ公開のみ）
- ai モデルやプロンプトのチューニング、追加の品質チェックルール
- ETL の細かな失敗通知・リトライ戦略の拡充

以上