Changelog
=========

すべての注目すべき変更点を時系列で記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 各バージョンはリリース日付きで記述
- カテゴリは Added / Changed / Fixed / Security / Deprecated / Removed を使用

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-28
-------------------

初回リリース。日本株自動売買フレームワーク「KabuSys」の基本機能群を実装しました。主な内容は以下の通りです。

Added
- パッケージ基礎
  - パッケージ初期化: kabusys.__init__ にバージョン情報と主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数/.env ローダー実装（kabusys.config）
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）
    - export KEY=val 形式やクォート/エスケープ、インラインコメントへの対応
    - override / protected キーの扱い（OS 環境変数保護）
    - 自動ロード無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）
    - Settings クラスによる型付きプロパティ公開（API トークン、DB パス、ログレベル、実行環境フラグ等）
    - env/log_level の値検証（許容値チェック）
- AI 関連
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を作成・保存
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応）
    - バッチ処理（最大 20 銘柄/回）、記事・文字数トリム、JSON Mode レスポンス検証
    - レート制限・ネットワーク断・サーバー5xx に対する指数バックオフのリトライ
    - レスポンスの堅牢なパース（前後余計なテキスト混入時に {} を抽出する復元ロジック）
    - テスト容易性のため _call_openai_api を差し替え可能に設計
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定
    - prices_daily / raw_news を参照、OpenAI への安全な呼び出しとリトライ処理を実装
    - LLM 呼び出し失敗時は macro_sentiment=0.0 とするフェイルセーフ
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - ルックアヘッドバイアス回避設計（datetime.today()/date.today() を参照しない、クエリに排他条件を使用）
- データ基盤
  - データ ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスによる実行結果の構造化（取得件数・保存件数・品質問題・エラーの集約）
    - 差分更新・バックフィル・品質チェック方針の実装要件を反映
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ
    - market_calendar が未取得の際の曜日ベースフォールバック、最大探索日数制限、安全性チェック（未来日異常検出）
    - J-Quants クライアント経由での取得と冪等保存フロー（fetch/save を呼び出す箇所を実装）
- リサーチ（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR・相対 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER, ROE の計算）
    - DuckDB を用いた SQL + Python 実装、データ不足時の None 扱い
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、rank/統計要約（factor_summary）
    - pandas 等外部依存を避けた実装、ランク計算での同順位の平均ランク対応
  - データ stats ユーティリティ再エクスポート（zscore_normalize を data.stats から再公開）
- テスト支援
  - AI モジュール内の外部 API 呼び出し箇所（_openai_api 関数）をモック差し替え可能に実装し、ユニットテストでの検証を容易に

Changed
- （初回リリースのため該当なし）

Fixed
- .env 読み込み時の I/O エラーに対して警告を発行して処理継続するように改善（kabusys.config）
- DuckDB executemany に対する互換性対策（空リストを送らないガード）を追加（news_nlp, pipeline）
- OpenAI レスポンスの不正な JSON や構造欠損時に例外を投げずフェイルセーフでスキップするようにし、DB の既存データを保護する処理を追加（news_nlp, regime_detector）

Security
- 各種 API キー/トークンは Settings 経由で必須チェックを行い、未設定時は明示的な ValueError を発生させる（OpenAI, Slack, J-Quants, kabu API など）
- 環境変数の上書き制御（protected set）により OS 環境変数が .env によって不意に上書きされないよう保護

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 実装上の設計方針（重要ポイント）
- すべての「日付基準処理」は明示的に target_date を引数として受け取り、datetime.today()/date.today() に依存しない設計でルックアヘッドバイアスを防止しています。
- DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT）で行い、部分失敗時に既存データを守るように設計しています。
- OpenAI 等外部 API 呼び出しは 429/ネットワーク断/タイムアウト/5xx をリトライ対象として指数バックオフを行い、致命的でない失敗はフェイルセーフで継続します。
- テスト容易性を考慮して、外部呼び出しをラップする内部関数（_call_openai_api 等）をモック差し替え可能にしています。

今後のロードマップ（例）
- strategy / execution / monitoring サブパッケージの具体的な売買ロジック・注文実行・監視機能の実装
- より細かな品質チェックモジュール（data.quality）の実装と、ETL の自動通知連携
- CI/CD テストカバレッジの拡充（DuckDB を用いた統合テスト等）

--- 

（注）本 CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴に基づく差分記録が別途ある場合は、そちらを優先してください。