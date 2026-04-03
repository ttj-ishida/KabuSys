CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の規約に従います。
リリースは "YYYY-MM-DD" 形式で日付付けしています。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-03
------------------

Added
- 初回公開（0.1.0）。
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys/__init__.py）。公開サブパッケージ: data, research, ai, execution, monitoring, strategy（__all__に一部を列挙）。
  - バージョン情報を __version__ に格納 ("0.1.0")。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートの判定は .git または pyproject.toml を探索）。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テストでの制御向け）。
  - 必須環境変数検査 _require と各種設定プロパティを実装（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE の設定、DB パス、監視閾値、環境種別・ログレベルなど）。
  - 環境値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）およびユーティリティプロパティ（is_live / is_paper / is_dev）を追加。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント評価（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）の JSON Mode を用いて一括解析。
    - チャンク処理（最大 20 銘柄/コール）、トークン肥大化対策（各銘柄ごと最大記事数・文字数トリム）を実装。
    - レスポンスのバリデーション（JSON 安定化処理、results 配列・型チェック、未知コード除外、数値チェック）、スコアの ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライを実装。部分失敗対策として、取得できた銘柄のみ ai_scores テーブルに置換（DELETE → INSERT）。
    - テスト補助のため OpenAI 呼び出し箇所を差し替え可能に（_call_openai_api を patch してモック化可能）。
    - calc_news_window ユーティリティ（JST ベースのニュース収集ウィンドウ計算）を提供。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF（1321）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news からのデータ取得、OpenAI 呼び出し、スコア合成、market_regime への冪等書き込みを行う。API 失敗時はマクロセンチメントを 0.0 にフォールバック。
    - OpenAI 呼び出しやリトライ処理を堅牢に実装（RateLimit, Timeout, 5xx などへの対応）。テストで差し替え可能な作り。
    - ルックアヘッドバイアスを避ける設計（target_date 未満のみ参照、datetime.today() を使わない）。

- データ基盤（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスで ETL の集計結果・品質問題・エラーを返却。
    - 差分取得、保存（jquants_client を通した冪等保存）、品質チェック（quality モジュール）を想定した設計。
    - テスト容易性のため id_token 注入や戻り値構造を明確化。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB にデータが無い場合は曜日（土日）によるフォールバックを行う一貫した設計。
    - JPX カレンダー差分取得ジョブ（calendar_update_job）を実装（J-Quants API 経由の差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル日数等の保護ロジックを導入して無限ループ・異常データを防止。
  - jquants_client を利用したデータ取得/保存の想定（fetch/save のラッパーと連携）。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M のリターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）等を DuckDB 上の SQL / Python 組合せで実装。
    - データ不足時の None 扱い、結果は (date, code) をキーとする辞書リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズンに対応、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）、ランク化ユーティリティ（同順位は平均ランク処理）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）出力。
  - データ正規化ユーティリティを data.stats（zscore_normalize）から再利用する公開設計。

- 全体設計上の重要点（横断）
  - DuckDB を主要なローカルデータストアとして採用。多くのモジュールが DuckDB 接続を受けて SQL を通じて処理。
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を直接参照しない設計を基本方針とする箇所が複数（AI スコアリング、レジーム判定など）。
  - DB 書き込み処理は冪等性を重視（DELETE→INSERT、ON CONFLICT での上書き等）。トランザクション BEGIN/COMMIT/ROLLBACK を適切に利用し、ROLLBACK の失敗もログに記録する。
  - OpenAI API 呼び出しは JSON Mode を利用し、レスポンスの堅牢な検証を実装。API エラーは基本的にフェイルセーフ（0.0 やスキップ）にフォールバックして上位プロセスの停止を避ける。
  - テスト容易性を考慮し、API 呼び出しポイントを差し替え可能にしている。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で注入する設計。設定値と自動 .env ロードの扱いに注意（KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを止められます）。

Notes / 開発者向けメモ
- 多くの箇所で外部 API（J-Quants, OpenAI）呼び出しがあるため、実運用時にはネットワーク・レート制限・API キー管理に注意してください。
- DuckDB のバージョン互換性（executemany の空リスト制約など）に配慮した実装がされているため、ローカル環境の DuckDB バージョン差で動作差が出る可能性があります。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定し、OpenAI 呼び出し関数をモック化することで外部依存を切り離せます。

--- 

（この CHANGELOG は、提示されたソースコードの内容から機能追加・設計方針・挙動を推測して作成しています。実際のコミット履歴やリリースノートと差異があり得ます。）