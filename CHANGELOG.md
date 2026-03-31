CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
以下は与えられたコードベースから推測して作成した初期リリースの変更履歴です。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-31
-------------------

### Added
- パッケージ初期リリースを追加（バージョン 0.1.0）。
- 基本パッケージ構成:
  - kabusys: 自動売買システムのルートパッケージ（__version__ = 0.1.0）。
  - サブパッケージの公開: data, strategy, execution, monitoring（__all__ によるエクスポート）。
- 環境設定管理（kabusys.config）:
  - .env/.env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml から検出）。
  - export KEY=val 形式やクォート／エスケープ、行末コメントのパースに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを提供し、必須変数チェック（_require）、型変換、検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - デフォルトパス・監視閾値（CPU/MEM/DISK）などの設定を提供。
- AI モジュール（kabusys.ai）:
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）:
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合。
    - OpenAI（gpt-4o-mini）の JSON Mode を使ったバッチ評価（最大 20 銘柄/チャンク）。
    - トークン肥大化対策（最大記事数、最大文字数トリム）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）と指数バックオフ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、型チェック、スコアクリップ）。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT）。部分失敗時の既存データ保護。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出のためのキーワードリストを搭載。
    - OpenAI 呼び出し（gpt-4o-mini）、JSON 解析、リトライ／バックオフ、フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api が単独実装）。
- Data モジュール（kabusys.data）:
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベースのフォールバック。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得し保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline, etl）:
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー収集など）。
    - 差分取得、保存（jquants_client を経由した冪等保存）、品質チェックの設計方針を実装。
    - 複数の内部ユーティリティ（テーブル存在チェック、最大日付取得など）。
  - jquants_client を想定した ETL フローのエントリポイント（kabusys.data.etl で ETLResult を re-export）。
- Research モジュール（kabusys.research）:
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev)。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が 0 or NULL の場合は None）、ROE（raw_financials から最新値）。
    - DuckDB SQL を用いた高性能な計算（ウィンドウ関数等）。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns、デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算（Spearman のランク相関）。
    - ランキング（rank）ユーティリティ（同順位は平均ランク）。
    - ファクターの統計サマリー（count/mean/std/min/max/median）。
- ログとフェイルセーフ:
  - 多くの箇所で詳細なログ出力を実装（info/debug/warning/exception）。
  - API 呼び出し失敗時にはゼロ値またはスキップで継続する設計（フェイルセーフ）。
- テストフレンドリー設計:
  - OpenAI 呼び出し部の差し替えポイントや、設定の自動ロード無効化フラグを用意。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 多くのエッジケースに対する防御的実装を導入:
  - OpenAI レスポンスの JSON 抽出や不正な型への耐性。
  - DuckDB の executemany の空リスト制約への対処（空チェックを追加）。
  - market_calendar の NULL 値検出時のフォールバックと警告ログ。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 外部 API キー（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、SLACK_* 等）は Settings により必須チェックを行う。環境変数の取り扱いは .env ファイルの読み込みで柔軟に管理。

Known issues / TODO
- ETL モジュールのソースが途中で切れている箇所が検出されました（pipeline._get_max_date の末尾に不完全なコード "return date.fro" が存在）。この部分は修正・補完が必要です。
- calc_value: PBR や 配当利回り等、将来的に追加予定の指標は未実装（コメントで参照あり）。
- OpenAI / J-Quants 等外部 API 依存:
  - 実行には適切な API キーと外部サービスへのアクセスが必要。
  - レート制限・コストに留意。
- 単体テストや統合テストは容易に差し替え可能な設計だが、実際のテスト実装は別途必要。
- Slack 通知等の実運用フローの実装は本リリースでの骨組みがあるが、運用設定やハンドラーの統合は追加作業が想定される。

作者 / 貢献者
- コードからの推測に基づく CHANGELOG のため、実際の貢献者情報はソース管理履歴を参照してください。

ライセンス
- 本 CHANGELOG はコードベースの解析に基づく推測を含みます。実際のリリースノートはリポジトリの履歴に基づいて更新してください。