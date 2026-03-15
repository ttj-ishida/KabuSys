# KabuSys

KabuSys は日本株の自動売買を想定した軽量なフレームワークの骨組みです。各種データ取得、売買戦略、注文実行、監視・ロギングを役割ごとに分割して実装できるように設計されています。本リポジトリは初期のパッケージ構成（スケルトン）を含み、これを基に機能を追加していくことを想定しています。

バージョン: 0.1.0

---

## 機能一覧（想定／今後の実装）

現在のリポジトリはパッケージ構造のみを提供します。各サブパッケージに実装を追加していくことで、以下のような機能を目指します。

- data
  - 市場データの取得（リアルタイム / 過去データ）
  - データ正規化・キャッシュ・リサンプリング
  - CSV や DB からの読み込み、外部API連携
- strategy
  - シグナル生成（テクニカル指標、機械学習モデル 等）
  - バックテストのための戦略インタフェース
  - パラメータ最適化・ファクトリ機能
- execution
  - 注文送信（成行・指値・逆指値 等）
  - 注文管理（注文状態の追跡、約定確認）
  - リスク管理（ポジション制限、注文頻度制御）
- monitoring
  - ログ収集、メトリクス出力（Prometheus 等）
  - アラート・ダッシュボード連携
  - モニタリング UI / レポート生成

---

## セットアップ手順

以下は一般的な Python プロジェクトのセットアップ手順です。リポジトリに `pyproject.toml` / `setup.py` / `requirements.txt` があれば適宜読み替えてください。

1. Python（3.8+ 推奨）を用意します。
2. 仮想環境を作成・有効化する（推奨）:
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1
3. 依存パッケージをインストールします（依存関係が記載されていない場合はここで必要なライブラリを追加してください）:
   - pip install -r requirements.txt
   - あるいは開発中は editable インストール:
     - pip install -e .
     - ※ リポジトリにインストール用の設定ファイルが必要です（pyproject.toml / setup.cfg 等）
4. （任意）テスト・静的解析ツールをインストール:
   - pip install pytest flake8 black

注意: 現状のリポジトリはスケルトンのみです。実際にブローカー API と連携して運用する場合は、API キー管理、SSL 設定、接続テストなどを必ず実施してください。

---

## 使い方（概念例）

現状はモジュールの雛形のみですが、想定される使い方の例を示します。各サブパッケージに実装を追加して、以下のように利用できます。

例: 基本的な使用フロー（擬似コード）
```python
from kabusys import __version__
from kabusys.data import DataFeed        # 仮想のクラス
from kabusys.strategy import Strategy    # 仮想のベースクラス
from kabusys.execution import Engine     # 仮想の実行エンジン
from kabusys.monitoring import Monitor   # 仮想の監視クラス

print("KabuSys version:", __version__)

# データフィードを作成（実装を追加する）
data_feed = DataFeed(source="kabu_api", symbols=["7203.T"])

# 戦略を作成（Strategy を継承して実装）
class MyStrategy(Strategy):
    def on_bar(self, bar):
        # シグナル生成ロジック
        pass

strategy = MyStrategy(params={})

# 実行エンジンの作成（注文送信・約定管理）
engine = Engine(data_feed=data_feed, strategy=strategy)

# 監視の設定（ログやメトリクス）
monitor = Monitor(engine)

# 実行開始
engine.run(live=True)  # backtest/live 等は実装次第
```

上記はあくまで使用イメージです。各クラスの API 設計はプロジェクト要件に合わせて実装してください。

---

## ディレクトリ構成

現在のリポジトリの主な構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py         — パッケージ初期化（バージョン情報）
    - data/
      - __init__.py       — データ関連モジュール群用パッケージ
    - strategy/
      - __init__.py       — 戦略ロジック用パッケージ
    - execution/
      - __init__.py       — 注文実行・エンジン用パッケージ
    - monitoring/
      - __init__.py       — 監視・ロギング用パッケージ

ツリー（簡易表示）
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ data/
   │  └─ __init__.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

---

## 開発のヒント / 実装の進め方

- まず各サブパッケージにインタフェース（抽象クラス）を定義しておくと、実装やテストが容易になります。
- 重要な点:
  - 注文や約定の処理は冪等性を考慮する（同一注文の二重送信に注意）
  - 実運用時は必ずサンドボックス / テスト環境で検証
  - API キーやシークレットは環境変数や安全なシークレット管理を利用
- ロギングと監視は初期段階から入れておくとデバッグが楽になります。

---

## 貢献・ライセンス

- 貢献方法: Issue や Pull Request で提案・実装を歓迎します。まず Issue で仕様や設計を議論してください。
- ライセンス: 本リポジトリにライセンスファイルが無ければ、使用前にライセンスを明確にしてください（例: MIT, Apache-2.0 等）。

---

必要があれば、各サブパッケージの具体的な公開 API（クラス・関数の雛形）や、サンプル実装（簡単なバックテストやダミー注文の実行例）を作成します。どの部分から実装を進めたいか教えてください。