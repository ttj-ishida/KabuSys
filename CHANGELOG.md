Keep a Changelog に準拠した CHANGELOG.md

すべての変更はセマンティックバージョニングに従います。  
このファイルは、リポジトリ内のコード（src/kabusys 以下）から推測した初期リリースの変更履歴を日本語でまとめたものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- なし

[0.1.0] - 2026-04-02
--------------------
Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: __version__ = "0.1.0"、公開サブパッケージ data, strategy, execution, monitoring を __all__ でエクスポート。
- 環境設定管理モジュール (kabusys.config)
  - .env ファイルと環境変数から設定を自動で読み込む仕組みを実装（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート自動検出ロジックを追加（.git または pyproject.toml を探索）。
  - .env 行パーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート
    - 無効行（空行、コメント、等）をスキップ
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム設定（env, log_level）などのプロパティを提供。未設定の必須環境変数は例外を送出する。
- AI 関連モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へバッチ送信して ai_scores へ書き込む。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を正確に実装。calc_news_window を公開。
    - 1チャンクあたり最大銘柄数や記事/文字数上限、JSON Mode を利用したレスポンス検証を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ、その他エラーはスキップ（フェイルセーフ）。
    - レスポンスの堅牢なバリデーションとスコアクリッピング（±1.0）。
    - テスト用に内部の OpenAI 呼び出し関数を patch で差し替え可能な設計。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しのフォールバック（API 失敗時 macro_sentiment=0.0）、再試行/エラーハンドリング、JSON パースの保護ロジックを実装。
    - LLM 呼び出しはモジュール内で独立実装し、news_nlp と相互に private 関数を共有しない設計。
- データプラットフォーム関連 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルと連携した営業日判定ユーティリティ群を提供（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - DB がない/不完全な場合は曜日ベースでフォールバックする安全策を実装。
    - JPX カレンダー差分取得ジョブ calendar_update_job を実装。バックフィル・健全性チェックを含む。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質チェック結果の格納、errors フィールド等）。
    - 差分取得、バックフィル、品質チェックを行う ETL 設計方針を実装。jquants_client による idempotent 保存を想定。
  - jquants_client のクライアント呼び出しを利用するインターフェースを想定（fetch/save 関数を呼ぶ設計）。
- 研究（Research）関連 (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER, ROE）等の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL とウィンドウ関数を用いて効率的に計算。
    - 欠損・データ不足時の None ハンドリングを明示。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（calc_ic）計算、rank、factor_summary を実装。
    - Spearman 相当のランク相関を自前で実装し、同順位の平均ランク処理などを行う。
- ロギングとデバッグ情報
  - 各モジュールで詳細な logger 呼び出しを追加（情報、警告、デバッグレベル）し、フェイルセーフ状況やデータ不足時の挙動がログに残る設計。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーや各種トークンは Settings による環境変数参照で管理。必須トークン未設定時は例外を投げる（安全性を向上）。

Notes / 実装上の設計上の重要点
- ルックアヘッドバイアス防止: date.today()/datetime.today() を判定ロジック内部で直接参照せず、必ず caller が target_date を渡す設計になっている（AI スコアリング / レジーム判定 / ETL / 研究機能すべてで遵守）。
- DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT 相当で既存行を上書き）。部分失敗時に他データを保護する工夫あり。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢な検査・復元処理を行う。API エラーの種類に応じてリトライ・フォールバックを使い分ける。
- テスト容易性: OpenAI 呼び出しを内部関数として抽象化し、unittest.mock.patch 等で差し替え可能にしている。

今後の予定（推測）
- strategy / execution / monitoring サブパッケージの具体実装（発注ロジック、実行エンジン、監視サービス）を追加予定。
- jquants_client の実体実装またはモックの提供による ETL の完全統合。
- ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づく追加機能の実装とチューニング。

付記
- 本 CHANGELOG は提示されたコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。必要であれば、実際の git ログやリリース日を反映して修正します。