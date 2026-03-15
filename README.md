# KabuSys

KabuSys は日本株の自動売買（アルゴリズムトレード）を想定した軽量なフレームワークのスケルトンです。データ取得、売買戦略、注文実行、監視・ロギングのためのサブパッケージを分離しており、各コンポーネントを実装して組み合わせることで自動売買システムを構築できます。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下の責務を持つ4つのモジュール構成を提供します。

- data: 市場データの取得・保存・前処理
- strategy: 売買戦略（シグナル生成）
- execution: 証券会社APIへの注文送信・注文管理
- monitoring: ログ、アラート、ダッシュボードなどの監視機能

現状はパッケージの骨組み（パッケージ初期化ファイル）のみが含まれており、各サブパッケージの具体的な実装はこれから追加していきます。

---

## 機能一覧（予定・設計方針）

- データ取得
  - 国内株式のリアルタイム/過去データの取得インターフェース
  - CSV/データベースへの保存
- 戦略
  - ストラテジーのプラグイン化（複数戦略の切替）
  - バックテスト用の簡易フレームワーク
- 注文実行
  - 注文送信・状態管理（成行/指値/取消）
  - 証券会社API（kabuステーション等）との接続ラッパー
- 監視
  - 取引ログの集約
  - 簡易ダッシュボード、アラート通知（メール/Slack等）
- 拡張性
  - モジュール単位での差し替えが容易なアーキテクチャ

---

## 要件（推奨）

- Python 3.8+
- （将来的に）各種外部ライブラリや証券会社APIクライアント（requirements.txt に記載予定）

---

## セットアップ手順

現状はパッケージの雛形のみのため、開発環境で使いやすくするための一般的な手順を示します。

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <リポジトリ>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージを使う方法（どちらか）

   オプション A — PYTHONPATH を使って直接実行（簡易）
   - プロジェクトのルートから次のように実行します:
     - Unix/macOS:
       - PYTHONPATH=src python -c "import kabusys; print(kabusys.__version__)"
     - Windows (PowerShell):
       - $env:PYTHONPATH = "src"; python -c "import kabusys; print(kabusys.__version__)"

   オプション B — 開発インストール（推奨、ただし setup.py / pyproject.toml が必要）
   - リポジトリに packaging ファイル（setup.py / pyproject.toml）を追加した上で:
     - pip install -e .

4. 依存関係
   - 現状 requirements.txt は含まれていません。実装にあわせて必要なライブラリ（requests, pandas, websockets 等）を追加してください。

5. 設定・認証情報
   - 実際の注文実行や市場データを利用する場合は、証券会社の API キーやエンドポイントなどの設定が必要です。環境変数や設定ファイルで管理することを推奨します。

---

## 使い方（例）

パッケージのインポートやサブパッケージの参照は次のように行います。

- パッケージ情報の確認:

  ```python
  import kabusys
  print(kabusys.__version__)   # "0.1.0"
  ```

- サブパッケージをインポート（現状は空のパッケージ）:

  ```python
  from kabusys import data, strategy, execution, monitoring

  # 実装例（各モジュールにクラスや関数を追加後）
  # df = data.fetch_price(... )
  # signal = strategy.SimpleMovingAverage().generate(df)
  # execution.BrokerClient().send_order(signal)
  # monitoring.Monitor().report(...)
  ```

- 開発時の推奨ワークフロー
  - data, strategy, execution, monitoring の各ディレクトリに実装を追加する
  - 単体テストを充実させる（pytest など）
  - 設定は安全に保ち、実注文テストは必ずサンドボックスで実行する

---

## ディレクトリ構成

現状のファイル構成（主要部分）:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ情報（__version__ 等）
│     ├─ data/
│     │  └─ __init__.py         # データ取得関連（未実装）
│     ├─ strategy/
│     │  └─ __init__.py         # 戦略関連（未実装）
│     ├─ execution/
│     │  └─ __init__.py         # 注文実行関連（未実装）
│     └─ monitoring/
│        └─ __init__.py         # 監視・ロギング（未実装）
└─ README.md
```

将来的には以下のようなファイルが追加されることを想定しています：
- src/kabusys/data/collector.py
- src/kabusys/strategy/base.py, strategies/*.py
- src/kabusys/execution/client.py, orders.py
- src/kabusys/monitoring/logger.py, dashboard.py
- tests/, examples/, docs/

---

## 開発ガイドライン（簡易）

- 各サブパッケージは責務を分離すること
- I/O（API呼び出し等）はインターフェースを定義し、テストしやすくする（モック可能）
- 実際の注文は必ずテスト環境で行うこと
- 機密情報（APIキー等）はリポジトリに含めない

---

## 貢献・ライセンス

- 貢献歓迎です。Issue や Pull Request を送ってください。
- 現在 README 上にライセンスは含まれていません。プロジェクトに適したライセンス（例: MIT, Apache-2.0 など）を追加してください。

---

ご不明点や README の追加修正（例えば具体的なサンプル戦略やパッケージ化手順の追記など）が必要であればお知らせください。